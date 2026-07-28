"""Populate EK General `question_as_set` from the Section A questions PDF.

The compilation (EK_General_SectionA_Questions_2016-2026.pdf) lists, per sitting
(e.g. "JULY 2016 — Questions 1..8"), the verbatim wording of questions 1–8 with their
(a)/(b) parts and printed marks, followed by derived "topic pill" lines. This script
extracts each question, keyed by (sitting, number), matches it to the existing EK
General question_instances by (diet label, question_number), and writes the wording
onto each mapped canonical answer's question_as_set (latest sitting wins for repeats).

    cd backend && python seeds/parse_ek_general_questions.py
"""
import os
import re
from collections import Counter, defaultdict

import pdfplumber

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject

PDF = os.environ.get(
    "EK_GENERAL_PDF",
    "C:/Users/Jenny/Downloads/EK_General_SectionA_Questions_2016-2026.pdf",
)

_ABBR = {"january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr",
         "may": "May", "june": "Jun", "july": "Jul", "august": "Aug",
         "september": "Sep", "october": "Oct", "november": "Nov", "december": "Dec"}

SITTING_RE = re.compile(r"^([A-Za-z]+)\s+(20\d{2})\b.*Questions\s+\d", re.IGNORECASE)
QNUM_RE = re.compile(r"^\s*([1-8])\.\s+(.*)")
MARKS_RE = re.compile(r"\(\d+\)")
HEADER_RE = re.compile(r"^Section A .*Management Level\s*$")
FOOTER_RE = re.compile(r"^Past questions .*Page \d+ of \d+\s*$")
NEWBLOCK_RE = re.compile(r"^\s*(?:\([a-z0-9]+\)|[a-z]\)|•)\s")


def reflow(text):
    """Join soft-wrapped lines into blocks; each (a)/(b)/(i) part starts a new block."""
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


def _trim_to_marks(lines):
    """Keep up to the last marks-bearing line, dropping trailing derived topic pills."""
    last = max((i for i, ln in enumerate(lines) if MARKS_RE.search(ln)), default=len(lines) - 1)
    return lines[:last + 1]


def parse_pdf(path):
    """Return {(diet_label, qnum): wording}."""
    with pdfplumber.open(path) as pdf:
        lines = []
        for pg in pdf.pages:
            for ln in (pg.extract_text() or "").split("\n"):
                if not (HEADER_RE.match(ln) or FOOTER_RE.match(ln)):
                    lines.append(ln)

    out, sitting, qnum, buf = {}, None, None, []

    def flush():
        if sitting and qnum and buf:
            out[(sitting, qnum)] = reflow("\n".join(_trim_to_marks(buf)))

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
            flush()
            qnum = int(q.group(1))
            buf = [q.group(2)]
        elif qnum is not None:
            buf.append(ln)
    flush()
    return out


def run():
    parsed = parse_pdf(os.path.abspath(PDF))
    per_sitting = Counter(s for s, _ in parsed)
    print(f"Parsed {len(parsed)} questions across {len(per_sitting)} sittings "
          f"(sittings without exactly 8: {[s for s, n in per_sitting.items() if n != 8] or 'none'}).")

    app = create_app()
    with app.app_context():
        subject = db.session.execute(
            db.select(Subject).filter_by(slug="ek-general")
        ).scalar_one()

        # (diet label, qnum) -> [canonical_answer_id, ...]  and diet ordering
        rows = db.session.execute(
            db.select(Diet.label, Diet.sort_order, QuestionInstance.question_number,
                      QuestionInstance.canonical_answer_id)
            .join(QuestionInstance, QuestionInstance.diet_id == Diet.id)
            .join(CanonicalAnswer, QuestionInstance.canonical_answer_id == CanonicalAnswer.id)
            .where(CanonicalAnswer.subject_id == subject.id)
        ).all()
        key_to_answers = defaultdict(list)
        diet_order = {}
        for label, order, qn, caid in rows:
            n = int(re.sub(r"\D", "", qn or "") or 0)
            key_to_answers[(label, n)].append(caid)
            diet_order[label] = order

        # apply oldest -> newest so the most recent sitting's wording wins for repeats
        applied = matched_instances = 0
        unmatched = []
        for (label, n) in sorted(parsed, key=lambda k: diet_order.get(k[0], -1)):
            caids = key_to_answers.get((label, n))
            if not caids:
                unmatched.append((label, n))
                continue
            for caid in caids:
                db.session.get(CanonicalAnswer, caid).question_as_set = parsed[(label, n)]
                matched_instances += 1
            applied += 1

        db.session.commit()

        total = db.session.scalar(
            db.select(db.func.count(CanonicalAnswer.id)).where(CanonicalAnswer.subject_id == subject.id))
        with_q = db.session.scalar(
            db.select(db.func.count(CanonicalAnswer.id))
            .where(CanonicalAnswer.subject_id == subject.id, CanonicalAnswer.question_as_set.isnot(None)))
        db_keys = set(key_to_answers)
        print(f"Matched {applied}/{len(parsed)} parsed questions -> {matched_instances} instances.")
        print(f"Parsed keys with no DB instance: {unmatched or 'none'}")
        print(f"DB (diet,q) not present in PDF: "
              f"{sorted(db_keys - set(parsed)) or 'none'}")
        print(f"EK General canonical answers with question_as_set: {with_q}/{total} "
              f"({total - with_q} still blank — zero-occurrence reference entries).")


if __name__ == "__main__":
    run()
