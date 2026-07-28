"""Integrate the EK Electrical Section B questions PDF (questions 9, 10, 11 per sitting).

EK Electrical's existing rows have NULL question_number and — as it turned out — diet
assignments that don't match this authoritative paper (e.g. its "Jul 2016" held 5
questions, not 3). So rather than trust the old sitting layout, this rebuilds the
occurrence structure FROM the PDF (the authoritative record of what was set when):

  * parse 123 questions (Q9-11 across 41 sittings) verbatim;
  * match each to an existing canonical answer by a hybrid text score (token overlap +
    sequence ratio, against the answer's question text AND title) — robust to the DB's
    curated wording; repeats of a new question dedupe to one new canonical;
  * rebuild the 123 question_instances against the correct sittings, preserving the
    canonical answers (and their examiner feedback, reattached) and creating
    'answer pending' entries for questions with no existing answer.

    cd backend && python seeds/parse_ek_electrical_questions.py
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
    "EK_ELECTRICAL_PDF",
    "C:/Users/Jenny/Downloads/EK_Electrical_SectionB_Questions_2016-2026.pdf",
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
            "provide".split())

SITTING_RE = re.compile(r"^([A-Za-z]+)\s+(20\d{2})\b.*Questions\s+\d", re.IGNORECASE)
QNUM_RE = re.compile(r"^\s*(9|10|11)\.\s+(.*)")
MARKS_RE = re.compile(r"\(\d+\)")
HEADER_RE = re.compile(r"^Section B .*Management Level\s*$")
FOOTER_RE = re.compile(r"^Past questions .*Page \d+ of \d+\s*$")
NEWBLOCK_RE = re.compile(r"^\s*(?:\([a-z0-9]+\)|[a-z]\)|•)\s")


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
                 if not (HEADER_RE.match(ln) or FOOTER_RE.match(ln))]
    out, sitting, qnum, buf = {}, None, None, []

    def flush():
        if sitting and qnum and buf:
            last = max((i for i, l in enumerate(buf) if MARKS_RE.search(l)), default=len(buf) - 1)
            out[(sitting, qnum)] = reflow("\n".join(x.strip() for x in buf[:last + 1]))

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
    """Hybrid similarity of a PDF question to a canonical's [question_text, title]."""
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
        subject = db.session.execute(db.select(Subject).filter_by(slug="ek-electrical")).scalar_one()

        # capture existing canonicals' rep text, title, and examiner feedback (pre-delete)
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

        # PDF is authoritative for sittings/numbers -> rebuild the occurrences
        sub_answer_ids = list(titles)
        db.session.execute(delete(QuestionInstance).where(
            QuestionInstance.canonical_answer_id.in_(sub_answer_ids)))
        db.session.flush()

        diet_by_label = {d.label: d for d in db.session.execute(
            db.select(Diet).where(Diet.subject_id == subject.id)).scalars()}

        new_canon = []  # [(caid, [texts])] created this run, so new repeats dedupe
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
                db.session.get(CanonicalAnswer, caid).question_as_set = wording  # latest wins
                fbs = feedback.get(caid) or []
                fb = fbs[fb_idx[caid] % len(fbs)] if fbs else None
                fb_idx[caid] += 1
                n_existing += 1
                matched_canon.add(caid)
            else:
                # dedupe against new questions already created this run
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
        print(f"EK Electrical now: {n_diet} diets, {n_inst} instances, {n_ans} answers, "
              f"{n_qas} with question_as_set.")


if __name__ == "__main__":
    run()
