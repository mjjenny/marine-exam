"""Restore exam content from content_seed.json (produced by export_content.py).

Recreates subjects, topics, diets, canonical answers and question occurrences from
natural keys, so it works on a fresh migrated database in any environment.

Per subject it does a CLEAN re-import: it deletes that subject's existing answers,
diets and topics, then re-inserts from the seed. On an empty database this simply
loads everything; on a populated one it replaces each subject's content wholesale.

    cd backend && python seeds/import_content.py            # <- seeds/content_seed.json
    cd backend && python seeds/import_content.py in.json    # custom path
"""
import json
import os
import sys
from datetime import date

from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "content_seed.json")


def run():
    with open(os.path.abspath(SRC), encoding="utf-8") as fh:
        doc = json.load(fh)

    app = create_app()
    with app.app_context():
        for sub in doc["subjects"]:
            subject = db.session.execute(
                db.select(Subject).filter_by(slug=sub["slug"])
            ).scalar_one_or_none()
            if subject is None:
                subject = Subject(slug=sub["slug"], name=sub["name"], is_oral=sub.get("is_oral", False))
                db.session.add(subject)
                db.session.flush()
            else:
                subject.name = sub["name"]
                subject.is_oral = sub.get("is_oral", False)

            # clean this subject's content (answers first -> cascades its question rows)
            db.session.execute(delete(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
            db.session.execute(delete(Diet).where(Diet.subject_id == subject.id))
            db.session.execute(delete(Topic).where(Topic.subject_id == subject.id))
            db.session.flush()

            topic_row = {}
            for name in sub.get("topics", []):
                t = Topic(subject_id=subject.id, name=name)
                db.session.add(t)
                topic_row[name] = t

            diet_row = {}
            for d in sub.get("diets", []):
                dt = date.fromisoformat(d["date"]) if d.get("date") else None
                row = Diet(subject_id=subject.id, label=d["label"], date=dt,
                           sort_order=d.get("sort_order", 0))
                db.session.add(row)
                diet_row[d["label"]] = row
            db.session.flush()

            for a in sub["answers"]:
                topic = topic_row.get(a.get("topic"))
                ca = CanonicalAnswer(
                    subject_id=subject.id,
                    topic_id=topic.id if topic else None,
                    slug=a.get("slug"),
                    title=a.get("title"),
                    marks=a.get("marks"),
                    question_as_set=a.get("question_as_set"),
                    answer_text=a.get("answer_text") or "",
                    sketch_refs=a.get("sketch_refs") or [],
                )
                db.session.add(ca)
                db.session.flush()
                for o in a.get("occurrences", []):
                    diet = diet_row.get(o.get("diet"))
                    db.session.add(QuestionInstance(
                        canonical_answer_id=ca.id,
                        diet_id=diet.id if diet else None,
                        question_number=o.get("question_number"),
                        question_text_as_asked=o.get("question_text_as_asked"),
                        examiner_feedback_text=o.get("examiner_feedback_text"),
                        source=o.get("source"),
                        total_marks=o.get("total_marks"),
                        marks_parts=o.get("marks_parts"),
                    ))

        db.session.commit()

        # summary
        for sub in doc["subjects"]:
            s = db.session.execute(db.select(Subject).filter_by(slug=sub["slug"])).scalar_one()
            na = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id)).where(CanonicalAnswer.subject_id == s.id))
            ni = db.session.scalar(db.select(db.func.count(QuestionInstance.id))
                                   .join(CanonicalAnswer).where(CanonicalAnswer.subject_id == s.id))
            print(f"  restored {s.name:14} answers={na:>4} questions={ni:>4}")
        print("Restore complete.")


if __name__ == "__main__":
    run()
