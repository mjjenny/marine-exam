"""Re-seed EK Naval from the Section C PDF (EK_Naval_SectionC_Answers_Parts1and2).

Authoritative source for the EK Naval pilot. Uses ek_naval_pdf.json at repo root
(produced by the PDF parser): 123 coverage rows + 57 answer-bank entries in 10 topic
groups. Each canonical answer's slug IS its entry code (e01..e57); the coverage map
becomes the question_instances across 41 sittings. Idempotent clean re-import.

    cd backend && python seeds/seed_ek_naval_pdf.py
"""
import json
import os
import re
from datetime import date

from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic
from app.services.storage import StorageError, ensure_bucket, upload_fileobj

JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ek_naval_pdf.json")
SKETCH_DIR = os.path.join(os.path.dirname(__file__), "ek_naval_sketches")

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

_NEW_BLOCK = re.compile(
    r"^\s*(?:•|\d+[.)]|\([a-z0-9]+\)|[A-Za-z]\)|Source note:|Note:|Marks:)\s"
)


def reflow(text):
    """Join the PDF's soft-wrapped lines into markdown paragraphs / list items."""
    blocks, cur = [], ""
    for raw in (text or "").split("\n"):
        s = raw.strip()
        if not s:
            if cur:
                blocks.append(cur)
                cur = ""
            continue
        if _NEW_BLOCK.match(s) and cur:
            blocks.append(cur)
            cur = s
        elif cur:
            cur += " " + s
        else:
            cur = s
    if cur:
        blocks.append(cur)
    out = []
    for b in blocks:
        b = re.sub(r"^\s*•\s*", "- ", b)  # bullet char -> markdown list marker
        # "Source note:" paragraphs are the folded-in Model Additions -> marginalia
        m = re.match(r"^(Source note|Note):\s*(.*)$", b, re.S)
        if m:
            b = f"> **{m.group(1)}:** {m.group(2)}"
        out.append(b)
    return "\n\n".join(out)


def parse_sitting(label):
    mon, year = label.split()
    m = _MONTHS[mon.lower()]
    y = int(year)
    return f"{_ABBR[m]} {y}", date(y, m, 1), y * 100 + m


def upload_sketches(sketches, storage_ok):
    """Upload each sketch image to object storage; return sketch_refs [{path,caption}].
    Returns [] (with a warning) if storage isn't configured so seeding still works."""
    refs = []
    for s in sketches or []:
        path = os.path.join(SKETCH_DIR, s["file"])
        if not (storage_ok and os.path.exists(path)):
            continue
        with open(path, "rb") as fh:
            key = upload_fileobj(fh, s["file"], "image/png", prefix="sketches/ek-naval")
        refs.append({"path": key, "caption": s.get("caption")})
    return refs


def run():
    with open(os.path.abspath(JSON_PATH), encoding="utf-8") as fh:
        doc = json.load(fh)
    coverage, entries = doc["coverage"], doc["entries"]

    app = create_app()
    with app.app_context():
        subject = db.session.execute(
            db.select(Subject).filter_by(slug="ek-naval")
        ).scalar_one_or_none()
        if subject is None:
            raise SystemExit("EK Naval subject not found — run seed_dev.py first.")

        db.session.execute(delete(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
        db.session.execute(delete(Diet).where(Diet.subject_id == subject.id))
        db.session.execute(delete(Topic).where(Topic.subject_id == subject.id))
        db.session.flush()

        # object storage for sketches (degrade gracefully if not configured)
        storage_ok = True
        try:
            ensure_bucket()
        except StorageError as exc:
            storage_ok = False
            print(f"  [warn] storage unavailable, skipping sketch upload: {exc}")

        # topic groups
        topic_row = {}
        for e in entries.values():
            g = e["group"]
            if g not in topic_row:
                t = Topic(subject_id=subject.id, name=g)
                db.session.add(t)
                db.session.flush()
                topic_row[g] = t

        # 57 canonical answers, keyed by entry code
        answer_row = {}
        for code, e in entries.items():
            a = CanonicalAnswer(
                subject_id=subject.id,
                topic_id=topic_row[e["group"]].id,
                slug=code.lower(),  # slug IS the entry code (e39); index shows E39
                title=e["title"],
                question_as_set=reflow(e.get("question_as_set")) if e.get("question_as_set") else None,
                answer_text=reflow(e["answer_markdown"]),
                sketch_refs=upload_sketches(e.get("sketches"), storage_ok),
            )
            db.session.add(a)
            db.session.flush()
            answer_row[code] = a

        # 41 diets + 123 question instances from the coverage map
        diet_row = {}
        n_inst = 0
        for row in coverage:
            label, dt, order = parse_sitting(row["sitting"])
            if label not in diet_row:
                d = Diet(subject_id=subject.id, label=label, date=dt, sort_order=order)
                db.session.add(d)
                db.session.flush()
                diet_row[label] = d
            db.session.add(
                QuestionInstance(
                    canonical_answer_id=answer_row[row["code"]].id,
                    diet_id=diet_row[label].id,
                    question_number=f"Q{row['q']}",
                    question_text_as_asked=row["question"],
                    examiner_feedback_text=None,
                    source=None,
                )
            )
            n_inst += 1

        db.session.commit()
        n_zero = sum(1 for c in entries if not any(r["code"] == c for r in coverage))
        n_sketch = sum(len(a.sketch_refs) for a in answer_row.values())
        n_qas = sum(1 for a in answer_row.values() if a.question_as_set)
        print(
            f"EK Naval (PDF) imported: {len(topic_row)} topics, {len(answer_row)} answers "
            f"({n_zero} not in coverage, {n_qas} with question-as-set), {len(diet_row)} diets, "
            f"{n_inst} question instances, {n_sketch} sketches uploaded."
        )


if __name__ == "__main__":
    run()
