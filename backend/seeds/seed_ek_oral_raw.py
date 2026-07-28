"""EK Oral — DIRECT / RAW ingestion of both C/E Orals PDFs.

No mapping, grouping, de-duplication or cross-referencing. Each self-contained
question/topic block in each PDF becomes its own flat entry, with the text extracted
and stored as-is:

  * Detailed Volume  -> each "Q<nums>. <desc>" block: title = the description, answer =
    the answer body that follows.
  * Master Guide     -> each "X.Y Title (…)" subtopic block: title = the topic, answer =
    the guide text that follows.

EK Oral is flat (is_oral=True, diet_id = NULL). Idempotent clean re-import.

    cd backend && python seeds/seed_ek_oral_raw.py
"""
import os
import re

import pdfplumber
from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

MG = os.environ.get("EK_ORAL_MASTER_PDF", "F:/UK CL1/Claude/Orals/CE_Orals_Master_Guide_and_Drawing_Pack.pdf")
DV = os.environ.get("EK_ORAL_DETAIL_PDF", "F:/UK CL1/Claude/Orals/CE_Orals_COMPLETE_Detailed_Volume.pdf")


def extract_dv_blocks(dv):
    body = "\n".join((dv.pages[i].extract_text() or "") for i in range(9, 89))
    body = re.sub(r"(?m)^[▲◆]?\s*INDEX\s*$", "", body)
    body = re.sub(r"(?m)^Chief Engineer Orals.*Detailed Volume\s*\d*\s*$", "", body)
    lines = body.split("\n")
    out, cur, part = [], None, ""
    grp = re.compile(r"^(Q[\d/\s]+)\.\s+(.+)$")
    for i, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"^Part\s+\d+\s*$", s) and i + 1 < len(lines):
            part = lines[i + 1].strip(); continue
        m = grp.match(s)
        if m and re.search(r"\d", m.group(1)):
            if cur:
                out.append(cur)
            cur = {"part": part, "desc": m.group(2).strip(), "lines": []}
        elif cur is not None:
            cur["lines"].append(s)
    if cur:
        out.append(cur)
    for g in out:
        g["answer"] = re.sub(r"\n{2,}", "\n\n", "\n".join(g["lines"]).strip())
    return out


def extract_mg_blocks(mg):
    body = "\n".join((mg.pages[i].extract_text() or "") for i in range(5, 59))
    body = re.sub(r"(?m)^INDEX\s*$", "", body)
    head = re.compile(r"(\d\.\d+)\s+([^\n(]+?)\s*\((?:consolidates|context for)\s+[Q\d,\s–\-]+?\)", re.S)
    ms = list(head.finditer(body))
    out, seen = [], set()
    for i, m in enumerate(ms):
        key = m.group(1)
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        answer = re.sub(r"\n{2,}", "\n\n", body[m.end():(ms[i + 1].start() if i + 1 < len(ms) else len(body))]).strip()
        if key in seen:  # a subtopic may have both a 'consolidates' and 'context for' heading
            out[[o["key"] for o in out].index(key)]["answer"] = max(
                out[[o["key"] for o in out].index(key)]["answer"], answer, key=len)
            continue
        seen.add(key)
        out.append({"key": key, "title": title, "answer": answer})
    return out


def run():
    mg, dv = pdfplumber.open(MG), pdfplumber.open(DV)
    dv_blocks = extract_dv_blocks(dv)
    mg_blocks = extract_mg_blocks(mg)
    print(f"Extracted {len(dv_blocks)} Detailed-Volume blocks + {len(mg_blocks)} Master-Guide blocks.")

    app = create_app()
    with app.app_context():
        subject = db.session.execute(db.select(Subject).filter_by(slug="ek-oral")).scalar_one()
        # wipe every EK Oral entry/mapping from the previous ingestion
        db.session.execute(delete(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
        db.session.execute(delete(Diet).where(Diet.subject_id == subject.id))
        db.session.execute(delete(Topic).where(Topic.subject_id == subject.id))
        db.session.flush()

        def add_entry(slug, title, answer, source):
            a = CanonicalAnswer(subject_id=subject.id, topic_id=None, slug=slug,
                                title=title[:200], question_as_set=None,
                                answer_text=answer or "", sketch_refs=[])
            db.session.add(a); db.session.flush()
            db.session.add(QuestionInstance(
                canonical_answer_id=a.id, diet_id=None, question_number=None,
                question_text_as_asked=title, examiner_feedback_text=None, source=source))

        for i, g in enumerate(dv_blocks, 1):
            add_entry(f"oral-dv-{i}", g["desc"], g["answer"], "Detail")
        for b in mg_blocks:
            add_entry(f"oral-mg-{b['key'].replace('.', '-')}", b["title"], b["answer"], "Guide")

        db.session.commit()
        n_ans = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id)).where(CanonicalAnswer.subject_id == subject.id))
        n_inst = db.session.scalar(db.select(db.func.count(QuestionInstance.id))
                                   .join(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
        n_empty = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id))
                                    .where(CanonicalAnswer.subject_id == subject.id, CanonicalAnswer.answer_text == ""))
        print(f"EK Oral (raw): {n_ans} entries ({len(dv_blocks)} Detailed Volume + {len(mg_blocks)} Master Guide), "
              f"{n_inst} rows, {n_empty} with no answer text. Flat, no diets, no mapping.")


if __name__ == "__main__":
    run()
