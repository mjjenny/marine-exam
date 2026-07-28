"""Integrate the EK Motor 040-13 question bank PDF (9 questions per diet, numbered 1-9).

Same PDF-authoritative rebuild as EK Electrical: the existing DB sitting/number layout
is treated as unreliable; the PDF is the authoritative record of what was set when.
Parses 378 verbatim questions across 42 diets, matches each to an existing EK Motor
answer by hybrid text similarity (token overlap + sequence ratio vs the answer's
question text AND title), rebuilds the occurrences against the correct sittings
(preserving answers + examiner feedback), and creates 'answer pending' entries for
genuinely new questions. Any DB-only diet left empty by the rebuild is removed so the
subject ends at exactly 42 diets / 378 questions.

    cd backend && python seeds/parse_ek_motor_questions.py
"""
import os
import re
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher

import pdfplumber
from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject

PDF = os.environ.get(
    "EK_MOTOR_PDF",
    "C:/Users/Jenny/Downloads/EK_Motor_040-13_Question_Bank_2016-2026.pdf",
)
THRESHOLD = 0.55
_ABBR = {"january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr",
         "may": "May", "june": "Jun", "july": "Jul", "august": "Aug",
         "september": "Sep", "october": "Oct", "november": "Nov", "december": "Dec"}
_MONTHNUM = {v: i for i, v in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_STOP = set("with reference to the of and a an for each following explain state describe "
            "that this these are used when why how what which type types system systems ship "
            "ships aid sketch diagram aboard board vessel vessels part parts marks mark "
            "provide total".split())

# sitting header: "Month YYYY" or "DD Month YYYY" (later diets print the exam day)
SITTING_RE = re.compile(r"^(?:\d{1,2}\s+)?([A-Za-z]+)\s+(20\d{2})\s*$")
# running page header on continuation pages: "<sitting> 9 Q"
RUNHDR_RE = re.compile(r"^(?:\d{1,2}\s+)?[A-Za-z]+\s+20\d{2}\s+\d+\s*Q\s*$", re.IGNORECASE)
FOOTER_RE = re.compile(r"^040-13 Engineering Knowledge.*Page \d+ of \d+\s*$")
RUBRIC_RE = re.compile(r"^(040-13 . ENGINEERING KNOWLEDGE|Attempt SIX questions)", re.IGNORECASE)
QNUM_RE = re.compile(r"^\s*([1-9])\.\s+(.*)")
NEWBLOCK_RE = re.compile(r"^\s*(?:\([a-z0-9]+\)|[a-z]\)|•|Total\s+\d)\s")


def reflow(text):
    blocks, cur = [], ""
    for raw in text.split("\n"):
        s = raw.strip()
        if not s:
            if cur:
                blocks.append(cur); cur = ""
            continue
        if NEWBLOCK_RE.match(s) and cur:
            blocks.append(cur); cur = s
        elif cur:
            cur += " " + s
        else:
            cur = s
    if cur:
        blocks.append(cur)
    return "\n\n".join(blocks)


def parse_pdf(path):
    with pdfplumber.open(path) as pdf:
        lines = [ln for pg in pdf.pages for ln in (pg.extract_text() or "").split("\n")
                 if not (FOOTER_RE.match(ln) or RUBRIC_RE.match(ln) or RUNHDR_RE.match(ln))]
    out, sitting, qnum, buf = {}, None, None, []

    def flush():
        if sitting and qnum and buf:
            out[(sitting, qnum)] = reflow("\n".join(x.strip() for x in buf))

    for ln in lines:
        m = SITTING_RE.match(ln)
        if m and m.group(1).lower() in _ABBR:
            flush(); buf, qnum = [], None
            sitting = f"{_ABBR[m.group(1).lower()]} {m.group(2)}"
            continue
        if sitting is None:
            continue
        q = QNUM_RE.match(ln)
        if q:
            flush(); qnum = int(q.group(1)); buf = [q.group(2)]
        elif qnum is not None:
            buf.append(ln)
    flush()
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def _toks(s):
    return {w for w in _norm(s).split() if len(w) > 3 and w not in _STOP}


def _score(wording, texts):
    pt = _toks(wording)
    best = 0.0
    for ct in texts:
        c = _toks(ct)
        if not c:
            continue
        inter = len(pt & c)
        overlap = inter / min(len(pt), len(c)) if pt and c else 0
        seq = SequenceMatcher(None, _norm(wording), _norm(ct)).ratio()
        best = max(best, seq, overlap if inter >= 3 else 0)
    return best


def _title(wording):
    first = re.sub(r"\s*\(\d+\)\s*$", "", wording.split("\n")[0].strip()).rstrip(":;. ")
    return (first[:70].rstrip() + "…") if len(first) > 72 else first


def _slug(base):
    base = re.sub(r"[^a-z0-9]+", "-", (base or "").lower()).strip("-") or "entry"
    slug, n = base, 2
    while db.session.scalar(db.select(CanonicalAnswer.id).filter_by(slug=slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def _order(key):
    mon, yr = key[0].split()
    return (int(yr), _MONTHNUM[mon], key[1])


def run():
    parsed = parse_pdf(os.path.abspath(PDF))
    print(f"Parsed {len(parsed)} questions across {len({s for s, _ in parsed})} sittings.")

    app = create_app()
    with app.app_context():
        subject = db.session.execute(db.select(Subject).filter_by(slug="ek-motor")).scalar_one()

        rep, feedback = {}, defaultdict(list)
        for caid, qt, fb in db.session.execute(
            db.select(QuestionInstance.canonical_answer_id, QuestionInstance.question_text_as_asked,
                      QuestionInstance.examiner_feedback_text)
            .join(CanonicalAnswer, QuestionInstance.canonical_answer_id == CanonicalAnswer.id)
            .where(CanonicalAnswer.subject_id == subject.id)
        ).all():
            if len(qt or "") > len(rep.get(caid, "")):
                rep[caid] = qt
            if fb and fb not in feedback[caid]:
                feedback[caid].append(fb)
        titles = {a.id: a.title for a in db.session.execute(
            db.select(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id)).scalars()}
        existing = [(caid, [rep.get(caid, ""), titles.get(caid, "")]) for caid in titles]

        sub_answer_ids = list(titles)
        db.session.execute(delete(QuestionInstance).where(
            QuestionInstance.canonical_answer_id.in_(sub_answer_ids)))
        db.session.flush()

        diet_by_label = {d.label: d for d in db.session.execute(
            db.select(Diet).where(Diet.subject_id == subject.id)).scalars()}

        new_canon = []
        fb_idx = defaultdict(int)
        n_existing = n_new_occ = 0
        matched_canon = set()

        for key in sorted(parsed, key=_order):
            label, qnum = key
            wording = parsed[key]
            if label not in diet_by_label:
                mon, yr = label.split()
                d = Diet(subject_id=subject.id, label=label, date=date(int(yr), _MONTHNUM[mon], 1),
                         sort_order=int(yr) * 100 + _MONTHNUM[mon])
                db.session.add(d); db.session.flush()
                diet_by_label[label] = d
            diet = diet_by_label[label]

            best = max(existing, key=lambda c: _score(wording, c[1]))
            if _score(wording, best[1]) >= THRESHOLD:
                caid = best[0]
                db.session.get(CanonicalAnswer, caid).question_as_set = wording
                fbs = feedback.get(caid) or []
                fb = fbs[fb_idx[caid] % len(fbs)] if fbs else None
                fb_idx[caid] += 1
                n_existing += 1
                matched_canon.add(caid)
            else:
                bn = max(new_canon, key=lambda c: _score(wording, c[1]), default=None)
                if bn and _score(wording, bn[1]) >= THRESHOLD:
                    caid = bn[0]
                    db.session.get(CanonicalAnswer, caid).question_as_set = wording
                else:
                    ans = CanonicalAnswer(
                        subject_id=subject.id, topic_id=None, slug=_slug(_title(wording)),
                        title=_title(wording), question_as_set=wording, answer_text="", sketch_refs=[])
                    db.session.add(ans); db.session.flush()
                    new_canon.append((ans.id, [wording, ans.title]))
                    caid = ans.id
                fb = None
                n_new_occ += 1

            db.session.add(QuestionInstance(
                canonical_answer_id=caid, diet_id=diet.id, question_number=f"Q{qnum}",
                question_text_as_asked=wording, examiner_feedback_text=fb))

        # remove any DB-only diet left empty by the rebuild (keeps exactly the PDF's diets)
        empty = db.session.execute(
            db.select(Diet).where(
                Diet.subject_id == subject.id,
                ~db.select(QuestionInstance.id).where(QuestionInstance.diet_id == Diet.id).exists())
        ).scalars().all()
        for d in empty:
            db.session.delete(d)

        db.session.commit()

        n_diet = db.session.scalar(db.select(db.func.count(Diet.id)).where(Diet.subject_id == subject.id))
        n_inst = db.session.scalar(db.select(db.func.count(QuestionInstance.id))
                                   .join(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
        n_ans = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id)).where(CanonicalAnswer.subject_id == subject.id))
        n_qas = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id))
                                  .where(CanonicalAnswer.subject_id == subject.id, CanonicalAnswer.question_as_set.isnot(None)))
        print(f"Matched {n_existing} occurrences to existing answers ({len(matched_canon)}/"
              f"{len(existing)} canonicals used); {n_new_occ} occurrences were new -> "
              f"{len(new_canon)} new 'answer pending' entries.")
        print(f"Removed {len(empty)} empty DB-only diet(s).")
        print(f"EK Motor now: {n_diet} diets, {n_inst} instances, {n_ans} answers, "
              f"{n_qas} with question_as_set.")


if __name__ == "__main__":
    run()
