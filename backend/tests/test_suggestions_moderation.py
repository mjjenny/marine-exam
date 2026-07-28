"""Suggest-improvement submission, admin moderation, and answer_history versioning."""
from app.extensions import db
from app.models import AnswerHistory, CanonicalAnswer


def _answer_text(app, answer_id):
    with app.app_context():
        return db.session.get(CanonicalAnswer, answer_id).answer_text


def _history_count(app, answer_id):
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count(AnswerHistory.id)).where(
                AnswerHistory.canonical_answer_id == answer_id
            )
        )


# ── submission (spec 4.2 steps 1-2) ──────────────────────
def test_submit_requires_authentication(anon, content):
    resp = anon.post(
        f"/api/answers/{content['fuel_answer_id']}/suggestions",
        json={"suggested_text": "x"},
    )
    assert resp.status_code == 401


def test_submit_requires_approved_account(pending, content):
    resp = pending.post(
        f"/api/answers/{content['fuel_answer_id']}/suggestions",
        json={"suggested_text": "x"},
    )
    assert resp.status_code == 403


def test_submit_creates_pending_and_leaves_answer_untouched(approved, app, content):
    before = _answer_text(app, content["fuel_answer_id"])
    resp = approved.post(
        f"/api/answers/{content['fuel_answer_id']}/suggestions",
        json={"suggested_text": "Add a note on variable injection timing."},
    )
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "pending"
    # Live answer is unchanged by a mere suggestion.
    assert _answer_text(app, content["fuel_answer_id"]) == before


def test_submit_rejects_empty_text(approved, content):
    resp = approved.post(
        f"/api/answers/{content['fuel_answer_id']}/suggestions",
        json={"suggested_text": "   "},
    )
    assert resp.status_code == 400


def test_submit_missing_answer_404(approved, content):
    resp = approved.post("/api/answers/999999/suggestions", json={"suggested_text": "x"})
    assert resp.status_code == 404


# ── moderation queue (spec 4.2 steps 3-5) ────────────────
def _submit(approved, answer_id, text="Suggested improved text."):
    resp = approved.post(f"/api/answers/{answer_id}/suggestions", json={"suggested_text": text})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def test_moderation_list_is_admin_only(approved, content):
    assert approved.get("/api/admin/suggestions").status_code == 403


def test_moderation_list_includes_live_answer(admin, approved, content):
    _submit(approved, content["fuel_answer_id"])
    items = admin.get("/api/admin/suggestions?status=pending").get_json()
    assert len(items) == 1
    assert items[0]["answer"]["current_text"] == "Original fuel answer."
    assert items[0]["answer"]["subject"] == "EK Motor"


def test_approve_publishes_amended_text_and_versions(admin, approved, app, content):
    sid = _submit(approved, content["fuel_answer_id"], "raw suggestion")
    assert _history_count(app, content["fuel_answer_id"]) == 0

    resp = admin.post(
        f"/api/admin/suggestions/{sid}/approve",
        json={"final_text": "Amended by admin before publishing."},
    )
    assert resp.status_code == 200
    # New text is live, prior version archived.
    assert _answer_text(app, content["fuel_answer_id"]) == "Amended by admin before publishing."
    assert _history_count(app, content["fuel_answer_id"]) == 1


def test_approve_without_amend_uses_suggested_text(admin, approved, app, content):
    sid = _submit(approved, content["fuel_answer_id"], "verbatim suggestion")
    admin.post(f"/api/admin/suggestions/{sid}/approve", json={})
    assert _answer_text(app, content["fuel_answer_id"]) == "verbatim suggestion"


def test_reject_keeps_answer_untouched(admin, approved, app, content):
    before = _answer_text(app, content["fuel_answer_id"])
    sid = _submit(approved, content["fuel_answer_id"])
    resp = admin.post(f"/api/admin/suggestions/{sid}/reject")
    assert resp.get_json()["status"] == "rejected"
    assert _answer_text(app, content["fuel_answer_id"]) == before
    assert _history_count(app, content["fuel_answer_id"]) == 0


def test_cannot_review_twice(admin, approved, content):
    sid = _submit(approved, content["fuel_answer_id"])
    assert admin.post(f"/api/admin/suggestions/{sid}/approve", json={}).status_code == 200
    # Second action on an already-reviewed suggestion is rejected.
    assert admin.post(f"/api/admin/suggestions/{sid}/reject").status_code == 400


def test_approve_missing_suggestion_404(admin):
    assert admin.post("/api/admin/suggestions/999999/approve", json={}).status_code == 404
