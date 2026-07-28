"""Import the EK Electrical question bank from the two source files at repo root:

  - ek_electrical_topics.json   : 16 topics + per-question slug, topic_id, marks, verified_diets
  - ek_electrical_content.json  : per-slug question_text, answer_text, examiner_focus, sketch_description

Joined on `slug`. Performs a clean re-import of EK Electrical (deletes existing
EK Electrical topics/diets/answers/instances first) so the DB matches the sources
exactly and is safe to re-run.

  - topics table seeded for EK Electrical
  - one canonical_answers row per slug (topic_id + answer_text set, marks stored,
    sketch_refs left empty)
  - question_instances per verified diet, linked to the right answer + diet row
    (diets created as needed), with examiner_focus split sensibly across the diets

`examiner_focus` is one string per slug. Where it uses per-diet labels
("December 2018: ... July 2022: ..."), each labelled segment is assigned to its diet.
Where it is shared prose naming several sittings together, it is attached to the
earliest diet only (not duplicated identically onto every instance).

    cd backend && python seeds/seed_ek_electrical.py
"""
import json
import os
import re
from datetime import date

from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
TOPICS_PATH = os.path.join(ROOT, "ek_electrical_topics.json")
CONTENT_PATH = os.path.join(ROOT, "ek_electrical_content.json")

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DIET_RE = re.compile(rf"^({_MONTH_ALT})\.?\s+(\d{{4}})", re.IGNORECASE)
# A "Month YYYY:" label used inside examiner_focus to introduce a per-diet segment.
_LABEL_RE = re.compile(rf"\b({_MONTH_ALT})\.?\s+(\d{{4}})\s*:", re.IGNORECASE)

# Month-name variants per month number, for detecting inline diet mentions.
_MONTH_VARIANTS = {
    1: "january|jan", 2: "february|feb", 3: "march|mar", 4: "april|apr", 5: "may",
    6: "june|jun", 7: "july|jul", 8: "august|aug", 9: "september|sept|sep",
    10: "october|oct", 11: "november|nov", 12: "december|dec",
}
# Split into sentences at ". " (etc.) followed by a capital or "(" — safe against
# "A.C." style abbreviations (no space after the internal dots).
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _mentions(text, info):
    return re.search(
        rf"\b(?:{_MONTH_VARIANTS[info['month']]})\.?\s+{info['year']}\b",
        text, re.IGNORECASE,
    ) is not None


def parse_diet(raw):
    """"Jul 2018 (unverified)" -> ("Jul 2018", month, year, sort_order). None if bad."""
    m = _DIET_RE.match(raw.strip())
    if not m:
        return None
    month, year = _MONTHS[m.group(1).lower()], int(m.group(2))
    return f"{_ABBR[month]} {year}", month, year, year * 100 + month


def split_examiner_focus(text, diet_infos):
    """Split examiner_focus into per-diet feedback. Returns {diet_label: feedback}.

    - Labelled text ("December 2018: ... July 2022: ...") -> each segment to its diet,
      and any sentence inside a segment that names a *different* verified diet is peeled
      off and reassigned to that diet (e.g. a trailing "Variant 2 (July 2026) ..." line).
    - Shared prose with no per-diet labels -> attached to every sitting it names (or, if
      it names none, to all of the question's diets as general feedback).
    """
    text = (text or "").strip()
    if not text or not diet_infos:
        return {}

    def append(store, label, chunk):
        store[label] = (store[label] + " " + chunk).strip() if label in store else chunk

    earliest = min(diet_infos, key=lambda d: d["sort_order"])["label"]
    labels = list(_LABEL_RE.finditer(text))

    if not labels:
        named = [d["label"] for d in diet_infos if _mentions(text, d)]
        targets = named or [d["label"] for d in diet_infos]
        return {label: text for label in targets}

    def match_label(month, year):
        for d in diet_infos:
            if d["month"] == month and d["year"] == year:
                return d["label"]
        return earliest

    result = {}
    preamble = text[: labels[0].start()].strip()
    if preamble:
        append(result, earliest, preamble)

    for i, m in enumerate(labels):
        seg_end = labels[i + 1].start() if i + 1 < len(labels) else len(text)
        seg = text[m.start():seg_end].strip()
        own = match_label(_MONTHS[m.group(1).lower()], int(m.group(2)))
        kept = []
        for sentence in _SENTENCE_RE.split(seg):
            sentence = sentence.strip()
            if not sentence:
                continue
            other = next(
                (d["label"] for d in diet_infos
                 if d["label"] != own and _mentions(sentence, d)),
                None,
            )
            if other:
                append(result, other, sentence)
            else:
                kept.append(sentence)
        if kept:
            append(result, own, " ".join(kept))
    return result


def run():
    with open(os.path.abspath(TOPICS_PATH), encoding="utf-8") as fh:
        topics_doc = json.load(fh)
    with open(os.path.abspath(CONTENT_PATH), encoding="utf-8") as fh:
        content_doc = json.load(fh)

    content_by_slug = {a["slug"]: a for a in content_doc["answers"]}
    missing = [q["slug"] for q in topics_doc["questions"] if q["slug"] not in content_by_slug]
    if missing:
        raise SystemExit(f"content file missing slugs: {missing}")

    app = create_app()
    with app.app_context():
        subject = db.session.execute(
            db.select(Subject).filter_by(slug=topics_doc["subject_slug"])
        ).scalar_one_or_none()
        if subject is None:
            subject = Subject(name=topics_doc["subject"], slug=topics_doc["subject_slug"])
            db.session.add(subject)
            db.session.flush()

        # Clean re-import: drop existing EK Electrical content (cascades instances).
        db.session.execute(
            delete(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id)
        )
        db.session.execute(delete(Diet).where(Diet.subject_id == subject.id))
        db.session.execute(delete(Topic).where(Topic.subject_id == subject.id))
        db.session.flush()

        # 1. topics (map the file's local topic id -> new Topic row)
        topic_by_file_id = {}
        for t in topics_doc["topics"]:
            topic = Topic(subject_id=subject.id, name=t["name"])
            db.session.add(topic)
            db.session.flush()
            topic_by_file_id[t["id"]] = topic

        diet_by_label = {}
        n_answers = n_instances = n_feedback = 0

        for q in topics_doc["questions"]:
            content = content_by_slug[q["slug"]]
            topic = topic_by_file_id.get(q["topic_id"])

            answer = CanonicalAnswer(
                subject_id=subject.id,
                topic_id=topic.id if topic else None,
                slug=q["slug"],
                title=q.get("title"),
                marks=q.get("marks"),  # may be None (valid, incomplete)
                answer_text=content["answer_text"],
                sketch_refs=[],  # sketch upload not built yet
            )
            db.session.add(answer)
            db.session.flush()
            n_answers += 1

            # Resolve this question's diets and split its examiner focus across them.
            diet_infos = []
            for raw in q.get("verified_diets", []):
                parsed = parse_diet(raw)
                if not parsed:
                    continue
                label, month, year, order = parsed
                if label not in diet_by_label:
                    d = Diet(subject_id=subject.id, label=label,
                             date=date(year, month, 1), sort_order=order)
                    db.session.add(d)
                    db.session.flush()
                    diet_by_label[label] = d
                diet_infos.append(
                    {"label": label, "month": month, "year": year, "sort_order": order}
                )

            feedback_by_label = split_examiner_focus(content.get("examiner_focus"), diet_infos)

            for info in diet_infos:
                fb = feedback_by_label.get(info["label"])
                db.session.add(
                    QuestionInstance(
                        canonical_answer_id=answer.id,
                        diet_id=diet_by_label[info["label"]].id,
                        question_number=None,
                        question_text_as_asked=content["question_text"],
                        examiner_feedback_text=fb,
                    )
                )
                n_instances += 1
                if fb:
                    n_feedback += 1

        db.session.commit()
        print(
            f"EK Electrical imported: {len(topics_doc['topics'])} topics, "
            f"{n_answers} answers ({sum(1 for q in topics_doc['questions'] if q.get('marks') is None)} with null marks), "
            f"{len(diet_by_label)} diets, {n_instances} question instances "
            f"({n_feedback} with examiner feedback)."
        )


if __name__ == "__main__":
    run()
