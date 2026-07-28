"""Import the SAMPLE dev/demo content from sample_content.json.

NON-DESTRUCTIVE: it only inserts entries whose slug starts with "sample-" and skips
any that already exist, so it will not modify or delete your real ingested content.
Intended for a fresh/empty or demo database only.

    cd backend && python seeds/seed_sample.py
"""
import json
import os
import re
from datetime import date

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

JSON_PATH = os.path.join(os.path.dirname(__file__), "sample_content.json")
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _diet(subject_id, label, cache):
    if label in cache:
        return cache[label]
    d = db.session.execute(
        db.select(Diet).filter_by(subject_id=subject_id, label=label)
    ).scalar_one_or_none()
    if d is None:
        mon, yr = label.split()
        m, y = _MONTHS[mon[:3].lower()], int(yr)
        d = Diet(subject_id=subject_id, label=label, date=date(y, m, 1), sort_order=y * 100 + m)
        db.session.add(d)
        db.session.flush()
    cache[label] = d
    return d


def _title(question):
    t = re.sub(r"\s+", " ", question).strip().rstrip("?.")
    return (t[:70].rstrip() + "…") if len(t) > 72 else t


def run():
    with open(JSON_PATH, encoding="utf-8") as fh:
        doc = json.load(fh)

    app = create_app()
    with app.app_context():
        added = skipped = 0
        for slug, sub in doc["subjects"].items():
            subject = db.session.execute(
                db.select(Subject).filter_by(slug=slug)
            ).scalar_one_or_none()
            if subject is None:
                print(f"  [skip] subject '{slug}' not in DB (run seed_dev.py first)")
                continue

            topics, diets = {}, {}
            for e in sub["entries"]:
                if db.session.execute(
                    db.select(CanonicalAnswer.id).filter_by(slug=e["slug"])
                ).first():
                    skipped += 1
                    continue

                tname = e.get("topic")
                topic = None
                if tname:
                    if tname not in topics:
                        t = db.session.execute(
                            db.select(Topic).filter_by(subject_id=subject.id, name=tname)
                        ).scalar_one_or_none()
                        if t is None:
                            t = Topic(subject_id=subject.id, name=tname)
                            db.session.add(t)
                            db.session.flush()
                        topics[tname] = t
                    topic = topics[tname]

                ans = CanonicalAnswer(
                    subject_id=subject.id,
                    topic_id=topic.id if topic else None,
                    slug=e["slug"],
                    title=_title(e["question"]),
                    question_as_set=e["question"],
                    answer_text=e["answer"],
                    sketch_refs=[],
                )
                db.session.add(ans)
                db.session.flush()

                diet = None if sub.get("is_oral") else _diet(subject.id, e["diet"], diets)
                db.session.add(QuestionInstance(
                    canonical_answer_id=ans.id,
                    diet_id=diet.id if diet else None,
                    question_number=e.get("q"),
                    question_text_as_asked=e["question"],
                    examiner_feedback_text=None,
                    source="Sample",
                ))
                added += 1

        db.session.commit()
        print(f"Sample content: {added} entries added, {skipped} already present (skipped).")


if __name__ == "__main__":
    run()
