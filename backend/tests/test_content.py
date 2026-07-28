"""Read-only content routes + the approved-only gate."""
from datetime import date


def test_content_requires_authentication(anon, content):
    assert anon.get("/api/subjects").status_code == 401


def test_content_requires_approved_account(pending, content):
    assert pending.get("/api/subjects").status_code == 403


def test_list_subjects_has_diets_flag(approved, content):
    subjects = {s["slug"]: s for s in approved.get("/api/subjects").get_json()}
    assert subjects["ek-motor"]["has_diets"] is True
    assert subjects["ek-oral"]["has_diets"] is False


def test_subjects_expose_is_oral_flag(approved, content):
    # is_oral distinguishes the flat Oral subject from diet-based subjects, and is
    # independent of whether any diets exist yet (drives the topic-tab exclusion).
    subjects = {s["slug"]: s for s in approved.get("/api/subjects").get_json()}
    assert subjects["ek-oral"]["is_oral"] is True
    assert subjects["ek-motor"]["is_oral"] is False


def test_question_payload_carries_subject_is_oral(approved, content):
    written = approved.get(f"/api/questions/{content['qi_july_id']}").get_json()
    oral = approved.get(f"/api/questions/{content['qi_oral_id']}").get_json()
    assert written["subject"]["is_oral"] is False  # written -> topic tab shown
    assert oral["subject"]["is_oral"] is True       # oral -> topic tab suppressed


def test_subject_detail_includes_topics(approved, content):
    data = approved.get("/api/subjects/ek-motor").get_json()
    names = {t["name"] for t in data["topics"]}
    assert {"Fuel", "Cooling"} <= names


def test_diets_latest_first_with_counts(approved, content):
    diets = approved.get("/api/subjects/ek-motor/diets").get_json()
    assert [d["label"] for d in diets] == ["July 2025", "March 2025"]
    counts = {d["label"]: d["question_count"] for d in diets}
    assert counts["July 2025"] == 1 and counts["March 2025"] == 1


def test_diet_page_lists_its_questions(approved, content):
    data = approved.get(f"/api/diets/{content['july_id']}").get_json()
    assert data["label"] == "July 2025"
    assert len(data["questions"]) == 1
    assert data["subject"]["slug"] == "ek-motor"


def test_question_page_cross_diet_also_asked_in(approved, content):
    data = approved.get(f"/api/questions/{content['qi_july_id']}").get_json()
    assert data["feedback_label"] == "Examiner Feedback"
    assert data["diet"]["label"] == "July 2025"
    also = {a["diet_label"] for a in data["also_asked_in"]}
    assert also == {"March 2025"}


def test_oral_question_feedback_label_and_no_diet(approved, content):
    data = approved.get(f"/api/questions/{content['qi_oral_id']}").get_json()
    assert data["feedback_label"] == "What Examiner Would Drill Into"
    assert data["diet"] is None
    assert data["also_asked_in"] == []


def test_oral_flat_list_search(approved, content):
    hits = approved.get("/api/subjects/ek-oral/questions?q=enclosed").get_json()["questions"]
    assert len(hits) == 1
    # Case-insensitive
    assert approved.get("/api/subjects/ek-oral/questions?q=ENCLOSED").get_json()["questions"]


def test_oral_flat_list_topic_filter(approved, content):
    all_q = approved.get("/api/subjects/ek-oral/questions").get_json()["questions"]
    filtered = approved.get(
        f"/api/subjects/ek-oral/questions?topic_id={content['safety_topic_id']}"
    ).get_json()["questions"]
    assert len(all_q) == 1 and len(filtered) == 1
    # Non-matching topic yields nothing.
    assert approved.get(
        f"/api/subjects/ek-oral/questions?topic_id={content['fuel_topic_id']}"
    ).get_json()["questions"] == []


def test_topic_view_dedupes_and_lists_repeat_diets(approved, content):
    data = approved.get(f"/api/topics/{content['fuel_topic_id']}/questions").get_json()
    assert data["topic"]["name"] == "Fuel"
    assert data["topic"]["subject"]["slug"] == "ek-motor"
    # The shared fuel answer (2 diets) is ONE deduped row listing both diets latest-first.
    assert len(data["questions"]) == 1
    q = data["questions"][0]
    assert q["repeat_count"] == 2
    assert q["repeat_diets"] == ["July 2025", "March 2025"]
    assert q["question_instance_id"] == content["qi_july_id"]  # latest occurrence


def test_diet_page_shows_repeat_history(approved, content):
    data = approved.get(f"/api/diets/{content['july_id']}").get_json()
    q = data["questions"][0]
    assert q["repeat_count"] == 2
    assert set(q["repeat_diets"]) == {"July 2025", "March 2025"}


def test_topic_view_requires_approved(pending, content):
    assert pending.get(
        f"/api/topics/{content['fuel_topic_id']}/questions"
    ).status_code == 403


def test_topic_view_missing_topic_404(approved, content):
    assert approved.get("/api/topics/999999/questions").status_code == 404


def test_zero_occurrence_answer_is_browsable(approved, content, app):
    """An answer with no question_instances still appears in the topic listing (by
    title) and is fetchable via /api/answers, so it isn't stranded."""
    from app.extensions import db
    from app.models import CanonicalAnswer, Subject

    with app.app_context():
        motor = db.session.execute(
            db.select(Subject).filter_by(slug="ek-motor")
        ).scalar_one()
        ans = CanonicalAnswer(
            subject_id=motor.id, topic_id=content["fuel_topic_id"],
            slug="reference-only-entry", title="Reference-only fuel note",
            answer_text="Some reference content.", sketch_refs=[],
        )
        db.session.add(ans)
        db.session.commit()
        aid = ans.id

    listing = approved.get(f"/api/topics/{content['fuel_topic_id']}/questions").get_json()
    row = [q for q in listing["questions"] if q["canonical_answer_id"] == aid]
    assert len(row) == 1
    assert row[0]["question_instance_id"] is None
    assert row[0]["repeat_count"] == 0
    assert row[0]["repeat_diets"] == []
    assert row[0]["question_text_as_asked"] == "Reference-only fuel note"

    detail = approved.get(f"/api/answers/{aid}").get_json()
    assert detail["title"] == "Reference-only fuel note"
    assert detail["answer_text"] == "Some reference content."
    assert detail["occurrences"] == []


def test_answer_endpoint_404(approved, content):
    assert approved.get("/api/answers/999999").status_code == 404


def test_subject_index_flat_list(approved, content):
    data = approved.get("/api/subjects/ek-motor/index").get_json()
    assert data["subject"]["slug"] == "ek-motor"
    entries = data["entries"]
    # two fuel occurrences (July + March), latest sitting first
    assert len(entries) == 2
    assert [e["sitting"] for e in entries] == ["July 2025", "March 2025"]
    first = entries[0]
    assert {"question_instance_id", "sitting", "q", "question", "status"} <= set(first)
    assert first["q"] == "1"  # "Q1" -> "1"
    assert first["question"] == "Describe fuel injection timing effects."


def test_subject_index_requires_approved(pending, content):
    assert pending.get("/api/subjects/ek-motor/index").status_code == 403


def test_index_sorts_future_diet_by_date(approved, content, app):
    """A diet added later with a future date sorts to the top of the index even when
    its sort_order was left at the default — ordering is driven by the diet date, so
    new diets (Oct 2026, Dec 2026 …) slot in chronologically with no bookkeeping."""
    from app.extensions import db
    from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject

    with app.app_context():
        motor = db.session.execute(
            db.select(Subject).filter_by(slug="ek-motor")
        ).scalar_one()
        future = Diet(
            subject_id=motor.id, label="Oct 2026", date=date(2026, 10, 1), sort_order=0
        )
        db.session.add(future)
        db.session.flush()
        ans = CanonicalAnswer(
            subject_id=motor.id, slug="e58", title="Future entry",
            answer_text="", sketch_refs=[],
        )
        db.session.add(ans)
        db.session.flush()
        db.session.add(
            QuestionInstance(
                canonical_answer_id=ans.id, diet_id=future.id, question_number="Q1",
                question_text_as_asked="A future question.",
            )
        )
        db.session.commit()

    entries = approved.get("/api/subjects/ek-motor/index").get_json()["entries"]
    # latest date first, ahead of the 2025 diets, despite sort_order=0
    assert entries[0]["sitting"] == "Oct 2026"
    assert [e["sitting"] for e in entries[:3]] == ["Oct 2026", "July 2025", "March 2025"]


def test_answer_pending_flag(approved, content, app):
    """A brand-new entry with no answer text is flagged answer_pending on both the
    /answers and /questions payloads; a normal answer is not."""
    from app.extensions import db
    from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject

    with app.app_context():
        motor = db.session.execute(
            db.select(Subject).filter_by(slug="ek-motor")
        ).scalar_one()
        blank = CanonicalAnswer(
            subject_id=motor.id, slug="e58", title="Pending entry",
            answer_text="", sketch_refs=[],
        )
        db.session.add(blank)
        db.session.flush()
        diet = Diet(subject_id=motor.id, label="Oct 2026", date=date(2026, 10, 1))
        db.session.add(diet)
        db.session.flush()
        qi = QuestionInstance(
            canonical_answer_id=blank.id, diet_id=diet.id, question_number="Q1",
            question_text_as_asked="A future question.",
        )
        db.session.add(qi)
        db.session.commit()
        aid, qid = blank.id, qi.id

    assert approved.get(f"/api/answers/{aid}").get_json()["answer_pending"] is True
    assert (
        approved.get(f"/api/questions/{qid}").get_json()["canonical_answer"]["answer_pending"]
        is True
    )
    # a published answer is not pending
    other = approved.get(f"/api/answers/{content['fuel_answer_id']}").get_json()
    assert other["answer_pending"] is False


def test_content_404s(approved, content):
    assert approved.get("/api/subjects/nope/diets").status_code == 404
    assert approved.get("/api/diets/999999").status_code == 404
    assert approved.get("/api/questions/999999").status_code == 404
