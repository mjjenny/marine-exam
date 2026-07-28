"""Insert the five subjects plus sample content for local dev.

Idempotent: safe to run repeatedly (looks up before inserting).

    cd backend && python seeds/seed_dev.py

Sample content is illustrative placeholder text, not real exam material — it exists
to exercise the content routes (diet pages, question pages, cross-diet "also asked in",
and the EK Oral flat list) end to end.
"""
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    CanonicalAnswer,
    Diet,
    QuestionInstance,
    Subject,
    Topic,
)

SUBJECTS = [
    ("EK Motor", "ek-motor"),
    ("EK General", "ek-general"),
    ("EK Naval", "ek-naval"),
    ("EK Electrical", "ek-electrical"),
    ("EK Oral", "ek-oral"),
]

# Sample diets for EK Motor (latest-first via sort_order).
MOTOR_DIETS = [
    ("July 2025", date(2025, 7, 1), 100),
    ("March 2025", date(2025, 3, 1), 99),
    ("March 2017", date(2017, 3, 1), 1),
]

MOTOR_TOPICS = ["Fuel", "Cooling", "Governors", "Lubrication"]
ORAL_TOPICS = ["Safety", "Emergencies", "Legislation"]


def get_or_create(model, defaults=None, **lookup):
    instance = db.session.execute(
        db.select(model).filter_by(**lookup)
    ).scalar_one_or_none()
    if instance:
        return instance, False
    params = {**lookup, **(defaults or {})}
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance, True


def seed_motor_content(motor, diets, topics):
    """A few canonical answers + question instances, incl. a cross-diet repeat."""
    # Canonical answer shared across two diets -> exercises "also asked in".
    fuel_answer, _ = get_or_create(
        CanonicalAnswer,
        subject_id=motor.id,
        topic_id=topics["Fuel"].id,
        answer_text=(
            "Correct fuel injection timing ensures the charge is injected at the "
            "optimum crank angle. Advanced timing raises peak pressure and NOx; "
            "retarded timing lowers efficiency and raises exhaust temperature and "
            "afterburning. [placeholder sample answer]"
        ),
        defaults={"sketch_refs": []},
    )
    get_or_create(
        QuestionInstance,
        canonical_answer_id=fuel_answer.id,
        diet_id=diets["July 2025"].id,
        question_number="1",
        defaults={
            "question_text_as_asked": (
                "Describe the effects of incorrect fuel injection timing on a marine "
                "diesel engine."
            ),
            "examiner_feedback_text": (
                "Candidates should distinguish clearly between advanced and retarded "
                "timing and quantify the effect on peak pressure and exhaust temperature."
            ),
        },
    )
    get_or_create(
        QuestionInstance,
        canonical_answer_id=fuel_answer.id,
        diet_id=diets["March 2025"].id,
        question_number="3",
        defaults={
            "question_text_as_asked": (
                "With reference to fuel injection timing, explain how mistiming affects "
                "engine performance and emissions."
            ),
            "examiner_feedback_text": (
                "Weaker answers omitted the emissions angle (NOx vs afterburning)."
            ),
        },
    )

    # A cooling answer, single instance.
    cooling_answer, _ = get_or_create(
        CanonicalAnswer,
        subject_id=motor.id,
        topic_id=topics["Cooling"].id,
        answer_text=(
            "Jacket cooling water carries heat from cylinder liners and heads to the "
            "central cooler; outlet temperature is controlled by a thermostatic valve. "
            "[placeholder sample answer]"
        ),
        defaults={"sketch_refs": []},
    )
    get_or_create(
        QuestionInstance,
        canonical_answer_id=cooling_answer.id,
        diet_id=diets["July 2025"].id,
        question_number="2",
        defaults={
            "question_text_as_asked": (
                "Explain how jacket cooling water temperature is controlled and why it "
                "matters."
            ),
            "examiner_feedback_text": (
                "Look for mention of thermal stress from over-cooling as well as "
                "corrosion/deposits from running too cold."
            ),
        },
    )

    # A governors answer on the oldest diet.
    gov_answer, _ = get_or_create(
        CanonicalAnswer,
        subject_id=motor.id,
        topic_id=topics["Governors"].id,
        answer_text=(
            "A governor maintains set engine speed under varying load by adjusting fuel "
            "rack position; droop and stability are key characteristics. "
            "[placeholder sample answer]"
        ),
        defaults={"sketch_refs": []},
    )
    get_or_create(
        QuestionInstance,
        canonical_answer_id=gov_answer.id,
        diet_id=diets["March 2017"].id,
        question_number="1",
        defaults={
            "question_text_as_asked": (
                "Describe the operation of an engine speed governor and explain droop."
            ),
            "examiner_feedback_text": (
                "Common weakness: confusing droop with hunting/instability."
            ),
        },
    )


def seed_oral_content(oral, topics):
    """EK Oral: flat questions with diet_id = NULL."""
    entries = [
        (
            "Safety",
            "Enclosed space entry: what pre-entry checks and permits are required?",
            "Expect a systematic answer: risk assessment, atmosphere testing (O2, "
            "flammable, toxic), permit-to-work, standby person, and communications.",
        ),
        (
            "Emergencies",
            "Describe your immediate actions on discovering an engine room fire.",
            "Drill into the order of actions and the decision points for boundary "
            "cooling and fixed fire-fighting release.",
        ),
        (
            "Legislation",
            "What are the survey and certification requirements under MARPOL Annex VI?",
            "Candidates should reference the relevant certificates and the examiner "
            "will probe on emission control areas.",
        ),
    ]
    for topic_name, question, feedback in entries:
        ans, _ = get_or_create(
            CanonicalAnswer,
            subject_id=oral.id,
            topic_id=topics[topic_name].id,
            answer_text=f"[placeholder oral answer] {question}",
            defaults={"sketch_refs": []},
        )
        get_or_create(
            QuestionInstance,
            canonical_answer_id=ans.id,
            diet_id=None,
            question_number=None,
            defaults={
                "question_text_as_asked": question,
                "examiner_feedback_text": feedback,
            },
        )


def run():
    app = create_app()
    with app.app_context():
        subjects = {}
        for name, slug in SUBJECTS:
            subj, created = get_or_create(
                Subject, slug=slug,
                defaults={"name": name, "is_oral": slug == "ek-oral"},
            )
            subjects[slug] = subj
            print(f"{'created' if created else 'exists '} subject: {name}")

        motor = subjects["ek-motor"]
        diets = {}
        for label, d, order in MOTOR_DIETS:
            diet, created = get_or_create(
                Diet, subject_id=motor.id, label=label,
                defaults={"date": d, "sort_order": order},
            )
            diets[label] = diet
            print(f"{'created' if created else 'exists '} diet:    {label}")

        motor_topics = {}
        for tname in MOTOR_TOPICS:
            topic, _ = get_or_create(Topic, subject_id=motor.id, name=tname)
            motor_topics[tname] = topic

        oral = subjects["ek-oral"]
        oral_topics = {}
        for tname in ORAL_TOPICS:
            topic, _ = get_or_create(Topic, subject_id=oral.id, name=tname)
            oral_topics[tname] = topic

        seed_motor_content(motor, diets, motor_topics)
        seed_oral_content(oral, oral_topics)

        db.session.commit()

        # summary counts
        n_answers = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id)))
        n_questions = db.session.scalar(db.select(db.func.count(QuestionInstance.id)))
        print(f"canonical_answers: {n_answers}, question_instances: {n_questions}")
        print("Seed complete.")


if __name__ == "__main__":
    run()
