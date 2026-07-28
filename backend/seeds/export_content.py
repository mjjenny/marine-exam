"""Export ALL exam content (every subject, topic, diet, canonical answer and question
occurrence) to a single committable JSON seed — the reproducible source of truth.

Read-only: it never modifies the database. Restore with import_content.py.

    cd backend && python seeds/export_content.py            # -> seeds/content_seed.json
    cd backend && python seeds/export_content.py out.json   # custom path
"""
import json
import os
import sys

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "content_seed.json")


def run():
    app = create_app()
    with app.app_context():
        subjects_out = []
        subjects = db.session.execute(db.select(Subject).order_by(Subject.id)).scalars().all()

        for s in subjects:
            topics = db.session.execute(
                db.select(Topic).filter_by(subject_id=s.id).order_by(Topic.id)
            ).scalars().all()
            topic_name = {t.id: t.name for t in topics}

            diets = db.session.execute(
                db.select(Diet).filter_by(subject_id=s.id).order_by(Diet.sort_order, Diet.id)
            ).scalars().all()
            diet_label = {d.id: d.label for d in diets}

            answers = db.session.execute(
                db.select(CanonicalAnswer).filter_by(subject_id=s.id).order_by(CanonicalAnswer.id)
            ).scalars().all()

            answers_out = []
            n_inst = 0
            for a in answers:
                occ = db.session.execute(
                    db.select(QuestionInstance)
                    .filter_by(canonical_answer_id=a.id)
                    .order_by(QuestionInstance.id)
                ).scalars().all()
                n_inst += len(occ)
                answers_out.append({
                    "slug": a.slug,
                    "title": a.title,
                    "topic": topic_name.get(a.topic_id),
                    "marks": a.marks,
                    "question_as_set": a.question_as_set,
                    "answer_text": a.answer_text,
                    "sketch_refs": a.sketch_refs or [],
                    "occurrences": [{
                        "diet": diet_label.get(qi.diet_id),
                        "question_number": qi.question_number,
                        "question_text_as_asked": qi.question_text_as_asked,
                        "examiner_feedback_text": qi.examiner_feedback_text,
                        "source": qi.source,
                        "total_marks": qi.total_marks,
                        "marks_parts": qi.marks_parts,
                    } for qi in occ],
                })

            subjects_out.append({
                "slug": s.slug,
                "name": s.name,
                "is_oral": s.is_oral,
                "topics": [t.name for t in topics],
                "diets": [{"label": d.label,
                           "date": d.date.isoformat() if d.date else None,
                           "sort_order": d.sort_order} for d in diets],
                "answers": answers_out,
            })
            print(f"  {s.name:14} topics={len(topics):>3} diets={len(diets):>3} "
                  f"answers={len(answers):>4} questions={n_inst:>4}")

        doc = {
            "_README": "Full exam-content seed exported from the live database. Restore "
                       "into an empty (migrated) database with import_content.py. Natural "
                       "keys only (subject slug, topic name, diet label) so it is portable "
                       "across environments. NOTE: sketch_refs point at object-storage keys; "
                       "the image files themselves live in MinIO/Spaces and must be restored "
                       "there separately (the EK Naval PNGs are in seeds/ek_naval_sketches/).",
            "subjects": subjects_out,
        }
        with open(os.path.abspath(OUT), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)

        size = os.path.getsize(OUT) / 1024
        totals = (sum(len(x["answers"]) for x in subjects_out),
                  sum(len(a["occurrences"]) for x in subjects_out for a in x["answers"]))
        print(f"Exported {len(subjects_out)} subjects, {totals[0]} answers, "
              f"{totals[1]} questions -> {OUT} ({size:.0f} KB)")


if __name__ == "__main__":
    run()
