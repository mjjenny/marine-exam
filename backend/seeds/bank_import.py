"""Shared importer for the topics+content question-bank schema (EK Naval, EK General).

Two files joined on topic_id:
  - <subject>_topics.json  : subject + topics [{topic_id, name, question_count}]
  - <subject>_content.json : subject + canonical_answers, each with a unique
    canonical_id, a topic_id (FK to a grouping topic), title, answer_markdown,
    examiner_focus[] (one question-level statement), and pre-parsed question_instances
    [{diet, question_number, marks_parts, total_marks, source, (note)}].

Mapping:
  - one Topic row per topics entry (name)
  - one CanonicalAnswer per content entry (slug = canonical_id, topic_id -> grouping
    Topic, answer_text = answer_markdown); answers may have zero instances
  - one Diet per distinct diet string ("December 2020" -> label "Dec 2020")
  - one QuestionInstance per instance, carrying question_number / total_marks /
    marks_parts / source, and examiner_feedback_text = examiner_focus[0]

Idempotent clean re-import per subject. Aborts and flags any unparseable diet string
rather than guessing or dropping it.
"""
import json
import os
import re
from datetime import date

from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


def parse_diet(raw):
    """"December 2020" -> ("Dec 2020", date(2020,12,1), 202012). None if unparseable."""
    m = re.fullmatch(r"\s*([A-Za-z]+)\s+(\d{4})\s*", raw or "")
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    year = int(m.group(2))
    return f"{_ABBR[month]} {year}", date(year, month, 1), year * 100 + month


# Rendered in place of a null answer_markdown (question verified, answer withheld).
# Plain text (no markdown syntax) since the app currently renders answer_text verbatim.
ANSWER_PENDING = "Answer pending — question verified; answer content not yet available."


def import_bank(subject_slug, topics_path, content_paths):
    """content_paths: a single path or a list of paths (a corpus split across files)."""
    with open(os.path.abspath(topics_path), encoding="utf-8") as fh:
        topics_doc = json.load(fh)
    if isinstance(content_paths, (str, bytes, os.PathLike)):
        content_paths = [content_paths]
    answers = []
    for cp in content_paths:
        with open(os.path.abspath(cp), encoding="utf-8") as fh:
            answers += json.load(fh)["canonical_answers"]

    topics = topics_doc["topics"]
    topic_names = {t["topic_id"]: t["name"] for t in topics}

    # Integrity: FK-subset + unique canonical_id.
    bad_fk = {a["topic_id"] for a in answers} - set(topic_names)
    if bad_fk:
        raise SystemExit(f"content references unknown topic_id(s): {sorted(bad_fk)}")
    cids = [a["canonical_id"] for a in answers]
    dupes = {cid for cid in cids if cids.count(cid) > 1}
    if dupes:
        raise SystemExit(f"duplicate canonical_id(s): {sorted(dupes)}")

    # Pre-flight: every diet string must parse. Flag rather than guess/drop.
    unparseable = sorted(
        {qi["diet"] for a in answers for qi in a["question_instances"]
         if parse_diet(qi["diet"]) is None}
    )
    if unparseable:
        raise SystemExit(
            "ABORT: unparseable diet strings (flagged, not guessed):\n  "
            + "\n  ".join(unparseable)
        )

    app = create_app()
    with app.app_context():
        subject = db.session.execute(
            db.select(Subject).filter_by(slug=subject_slug)
        ).scalar_one_or_none()
        if subject is None:
            raise SystemExit(f"subject '{subject_slug}' not found — run seed_dev.py first.")

        # Clean re-import (answers cascade to their instances).
        db.session.execute(delete(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
        db.session.execute(delete(Diet).where(Diet.subject_id == subject.id))
        db.session.execute(delete(Topic).where(Topic.subject_id == subject.id))
        db.session.flush()

        topic_row = {}
        for tid, name in topic_names.items():
            row = Topic(subject_id=subject.id, name=name)
            db.session.add(row)
            db.session.flush()
            topic_row[tid] = row

        diet_row = {}
        n_answers = n_instances = n_empty = n_placeholder = 0
        for a in answers:
            focus = a.get("examiner_focus") or []
            feedback = focus[0] if focus else None
            # answer_text is NOT NULL; a null answer_markdown becomes a visible placeholder.
            answer_text = a.get("answer_markdown")
            if answer_text is None:
                answer_text = ANSWER_PENDING
                n_placeholder += 1
            answer = CanonicalAnswer(
                subject_id=subject.id,
                topic_id=topic_row[a["topic_id"]].id,
                slug=a["canonical_id"],
                title=a.get("title"),
                answer_text=answer_text,
                sketch_refs=[],
            )
            db.session.add(answer)
            db.session.flush()
            n_answers += 1
            if not a["question_instances"]:
                n_empty += 1

            for qi in a["question_instances"]:
                label, dt, order = parse_diet(qi["diet"])
                if label not in diet_row:
                    d = Diet(subject_id=subject.id, label=label, date=dt, sort_order=order)
                    db.session.add(d)
                    db.session.flush()
                    diet_row[label] = d
                db.session.add(
                    QuestionInstance(
                        canonical_answer_id=answer.id,
                        diet_id=diet_row[label].id,
                        question_number=qi.get("question_number"),
                        question_text_as_asked=a["title"],
                        examiner_feedback_text=feedback,
                        total_marks=qi.get("total_marks"),
                        marks_parts=qi.get("marks_parts"),
                        source=qi.get("source"),
                    )
                )
                n_instances += 1

        db.session.commit()
        print(
            f"{subject_slug} imported: {len(topic_row)} topics, {n_answers} answers "
            f"({n_empty} with no diet occurrences, {n_placeholder} null->placeholder), "
            f"{len(diet_row)} diets, {n_instances} question instances. "
            "No unparseable diet strings."
        )
        return {
            "topics": len(topic_row), "answers": n_answers, "empty": n_empty,
            "diets": len(diet_row), "instances": n_instances, "placeholder": n_placeholder,
        }
