"""Admin-only routes: the member approval queue (step 5), the suggested-edit
moderation queue (step 7), and the Add-Diet tool (manual + PDF-assisted question entry)."""
import re
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from ..auth import admin_required
from ..extensions import db
from ..models import (
    AnswerHistory,
    CanonicalAnswer,
    Diet,
    QuestionInstance,
    Subject,
    SuggestedEdit,
    SuggestedEditSketch,
    Topic,
    User,
)
from ..models.moderation import SuggestedEditStatus
from ..models.user import UserStatus
from ..services.email import notify_user_approved
from ..services.pdf_parse import parse_exam_pdf

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _user_json(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "status": u.status.value,
        "is_admin": u.is_admin,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "expires_at": u.expires_at.isoformat() if u.expires_at else None,
    }


@bp.get("/users")
@admin_required
def list_users():
    """List users, optionally filtered by ?status=pending|approved|rejected."""
    status_arg = request.args.get("status")
    stmt = db.select(User)
    if status_arg:
        try:
            status = UserStatus(status_arg)
        except ValueError:
            return jsonify({"error": "invalid status filter"}), 400
        stmt = stmt.where(User.status == status)
    stmt = stmt.order_by(User.created_at.asc())
    users = db.session.execute(stmt).scalars().all()
    return jsonify([_user_json(u) for u in users])


@bp.get("/pending-count")
@admin_required
def pending_count():
    n = db.session.scalar(
        db.select(db.func.count(User.id)).where(User.status == UserStatus.pending)
    )
    return jsonify({"count": n or 0})


def _set_status(user_id: int, new_status: UserStatus):
    """Returns (user, error_response). One of them is always None."""
    user = db.get_or_404(User, user_id)
    if user.is_admin:
        return None, (jsonify({"error": "cannot change an admin account's status"}), 400)
    user.status = new_status
    db.session.commit()
    return user, None


@bp.post("/users/<int:user_id>/approve")
@admin_required
def approve_user(user_id):
    user, err = _set_status(user_id, UserStatus.approved)
    if err:
        return err
    notify_user_approved(user.email)
    return jsonify(_user_json(user))


@bp.post("/users/<int:user_id>/reject")
@admin_required
def reject_user(user_id):
    user, err = _set_status(user_id, UserStatus.rejected)
    if err:
        return err
    return jsonify(_user_json(user))


@bp.post("/users/<int:user_id>/revoke")
@admin_required
def revoke_user(user_id):
    """Immediately revoke a user's access (plagiarism / abuse protection)."""
    user, err = _set_status(user_id, UserStatus.revoked)
    if err:
        return err
    return jsonify(_user_json(user))


# ── Suggested-edit moderation queue (step 7) ─────────────
def _suggestion_json(se: SuggestedEdit) -> dict:
    """Serialize a suggestion alongside the live answer, for side-by-side review."""
    answer = db.session.get(CanonicalAnswer, se.canonical_answer_id)
    subject = db.session.get(Subject, answer.subject_id)
    topic = db.session.get(Topic, answer.topic_id) if answer.topic_id else None
    submitter = db.session.get(User, se.submitted_by_user_id)
    sample_question = db.session.scalar(
        db.select(QuestionInstance.question_text_as_asked)
        .where(QuestionInstance.canonical_answer_id == answer.id)
        .limit(1)
    )
    sketches = db.session.execute(
        db.select(SuggestedEditSketch).where(
            SuggestedEditSketch.suggested_edit_id == se.id
        )
    ).scalars().all()
    return {
        "id": se.id,
        "suggested_text": se.suggested_text,
        "status": se.status.value,
        "submitted_by": submitter.email if submitter else None,
        "submitted_at": se.submitted_at.isoformat() if se.submitted_at else None,
        "reviewed_at": se.reviewed_at.isoformat() if se.reviewed_at else None,
        "sketches": [{"id": sk.id, "path": sk.image_path} for sk in sketches],
        "answer": {
            "id": answer.id,
            "current_text": answer.answer_text,
            "subject": subject.name if subject else None,
            "topic": topic.name if topic else None,
            "sample_question": sample_question,
            "sketch_refs": answer.sketch_refs or [],
        },
    }


@bp.get("/suggestions")
@admin_required
def list_suggestions():
    """List suggestions, filtered by ?status= (default pending)."""
    status_arg = request.args.get("status", "pending")
    stmt = db.select(SuggestedEdit)
    if status_arg:
        try:
            status = SuggestedEditStatus(status_arg)
        except ValueError:
            return jsonify({"error": "invalid status filter"}), 400
        stmt = stmt.where(SuggestedEdit.status == status)
    stmt = stmt.order_by(SuggestedEdit.submitted_at.asc())
    suggestions = db.session.execute(stmt).scalars().all()
    return jsonify([_suggestion_json(se) for se in suggestions])


@bp.get("/suggestions/pending-count")
@admin_required
def suggestions_pending_count():
    n = db.session.scalar(
        db.select(db.func.count(SuggestedEdit.id)).where(
            SuggestedEdit.status == SuggestedEditStatus.pending
        )
    )
    return jsonify({"count": n or 0})


@bp.post("/suggestions/<int:suggestion_id>/approve")
@admin_required
def approve_suggestion(suggestion_id):
    """Publish a suggestion (optionally after amending its text).

    Logs the prior answer version to answer_history, writes the new text into the
    canonical answer, and marks the suggestion approved.
    """
    se = db.get_or_404(SuggestedEdit, suggestion_id)
    if se.status != SuggestedEditStatus.pending:
        return jsonify({"error": "suggestion has already been reviewed"}), 400

    data = request.get_json(silent=True) or {}
    # Admin may amend the text before publishing; default to the submitted text.
    final_text = (data.get("final_text") or se.suggested_text or "").strip()
    if not final_text:
        return jsonify({"error": "final text cannot be empty"}), 400

    answer = db.session.get(CanonicalAnswer, se.canonical_answer_id)

    # Audit: snapshot the version being replaced (text + sketches).
    db.session.add(
        AnswerHistory(
            canonical_answer_id=answer.id,
            previous_text=answer.answer_text,
            previous_sketch_refs=answer.sketch_refs,
        )
    )

    answer.answer_text = final_text

    # Promote any sketches attached to this suggestion onto the canonical answer.
    sketches = db.session.execute(
        db.select(SuggestedEditSketch).where(
            SuggestedEditSketch.suggested_edit_id == se.id
        )
    ).scalars().all()
    if sketches:
        # Reassign a new list so SQLAlchemy detects the JSONB change.
        refs = list(answer.sketch_refs or [])
        refs.extend({"path": sk.image_path, "caption": None} for sk in sketches)
        answer.sketch_refs = refs

    se.status = SuggestedEditStatus.approved
    se.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(
        {
            "id": se.id,
            "status": se.status.value,
            "answer_id": answer.id,
            "promoted_sketches": len(sketches),
        }
    )


@bp.post("/suggestions/<int:suggestion_id>/reject")
@admin_required
def reject_suggestion(suggestion_id):
    """Reject a suggestion. It stays in the table for audit; live answer untouched."""
    se = db.get_or_404(SuggestedEdit, suggestion_id)
    if se.status != SuggestedEditStatus.pending:
        return jsonify({"error": "suggestion has already been reviewed"}), 400

    se.status = SuggestedEditStatus.rejected
    se.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"id": se.id, "status": se.status.value})


# ── Add-Diet tool: manual + PDF-assisted question entry ──────────────────
_ENTRY_CODE = re.compile(r"^e(\d+)$")
_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
_FULL = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
         7: "July", 8: "August", 9: "September", 10: "October", 11: "November",
         12: "December"}


def _entry_code(slug):
    m = slug and _ENTRY_CODE.match(slug)
    return slug.upper() if m else None


def _uses_entry_codes(subject_id):
    slug = db.session.scalar(
        db.select(CanonicalAnswer.slug)
        .where(CanonicalAnswer.subject_id == subject_id, CanonicalAnswer.slug.op("~")("^e[0-9]+$"))
        .limit(1)
    )
    return slug is not None


def _next_entry_code(subject_id):
    """Next e-code (e58…) for a subject whose entries are code-keyed, else None."""
    codes = db.session.execute(
        db.select(CanonicalAnswer.slug).where(CanonicalAnswer.subject_id == subject_id)
    ).scalars().all()
    nums = [int(m.group(1)) for s in codes if (m := _ENTRY_CODE.match(s or ""))]
    return f"e{(max(nums) + 1) if nums else 1:02d}" if nums else None


def _unique_slug(base):
    """A globally-unique slug from `base`, adding a numeric suffix on collision."""
    base = re.sub(r"[^a-z0-9]+", "-", (base or "").lower()).strip("-") or "entry"
    slug, n = base, 2
    while db.session.scalar(db.select(CanonicalAnswer.id).filter_by(slug=slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def _diet_label(subject_id, month, year):
    """Format a diet label in the subject's existing style (full-month vs abbreviated)."""
    sample = db.session.scalar(
        db.select(Diet.label).where(Diet.subject_id == subject_id).limit(1)
    )
    full = bool(sample) and sample.split(" ")[0].lower() in {v.lower() for v in _FULL.values()}
    return f"{(_FULL if full else _ABBR)[month]} {year}"


def _entry_json(a):
    return {"canonical_answer_id": a.id, "code": _entry_code(a.slug),
            "slug": a.slug, "title": a.title or "(untitled)"}


@bp.get("/entries")
@admin_required
def list_entries():
    """Entries (canonical answers) for a subject, for the mapping dropdown."""
    slug = request.args.get("subject")
    subject = db.session.execute(
        db.select(Subject).filter_by(slug=slug)
    ).scalar_one_or_none()
    if subject is None:
        return jsonify({"error": "unknown subject"}), 404
    answers = db.session.execute(
        db.select(CanonicalAnswer)
        .where(CanonicalAnswer.subject_id == subject.id)
        .order_by(CanonicalAnswer.slug.nullslast(), CanonicalAnswer.id)
    ).scalars().all()
    return jsonify({
        "subject": {"slug": subject.slug, "name": subject.name},
        "uses_entry_codes": _uses_entry_codes(subject.id),
        "next_code": _entry_code(_next_entry_code(subject.id)) if _uses_entry_codes(subject.id) else None,
        "entries": [_entry_json(a) for a in answers],
    })


@bp.post("/questions")
@admin_required
def add_questions():
    """Commit one or more questions to a (new or existing) diet. Powers both the manual
    form (one item) and the PDF staging commit (many items). New questions default to
    'answer pending'; they appear in /subjects/<slug>/index immediately (no restart)."""
    data = request.get_json(silent=True) or {}
    subject = db.session.execute(
        db.select(Subject).filter_by(slug=(data.get("subject_slug") or ""))
    ).scalar_one_or_none()
    if subject is None:
        return jsonify({"error": "unknown subject"}), 404
    try:
        month, year = int(data.get("month")), int(data.get("year"))
    except (TypeError, ValueError):
        return jsonify({"error": "month and year are required"}), 400
    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        return jsonify({"error": "invalid month/year"}), 400
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "no questions to add"}), 400
    for it in items:
        if not (it.get("wording") or "").strip():
            return jsonify({"error": "every question needs wording"}), 400
        if not it.get("canonical_answer_id") and not (it.get("new_entry_title") or "").strip():
            return jsonify({"error": "map each question to an entry or give a new-entry title"}), 400

    # find-or-create the diet
    label = _diet_label(subject.id, month, year)
    diet = db.session.execute(
        db.select(Diet).filter_by(subject_id=subject.id, label=label)
    ).scalar_one_or_none()
    if diet is None:
        diet = Diet(subject_id=subject.id, label=label, date=date(year, month, 1),
                    sort_order=year * 100 + month)
        db.session.add(diet)
        db.session.flush()

    created = []
    for it in items:
        wording = it["wording"].strip()
        qnum = (it.get("question_number") or "").strip() or None
        if it.get("canonical_answer_id"):
            answer = db.session.get(CanonicalAnswer, it["canonical_answer_id"])
            if answer is None or answer.subject_id != subject.id:
                db.session.rollback()
                return jsonify({"error": "entry does not belong to this subject"}), 400
            if not (answer.question_as_set or "").strip():
                answer.question_as_set = wording  # seed the canonical question if blank
        else:
            answer = CanonicalAnswer(
                subject_id=subject.id, topic_id=None,
                slug=_next_entry_code(subject.id) or _unique_slug(it["new_entry_title"]),
                title=it["new_entry_title"].strip(),
                question_as_set=wording, answer_text="", sketch_refs=[],
            )
            db.session.add(answer)
            db.session.flush()  # assign id + so the next new e-code increments
        qi = QuestionInstance(
            canonical_answer_id=answer.id, diet_id=diet.id,
            question_number=qnum, question_text_as_asked=wording,
        )
        db.session.add(qi)
        db.session.flush()
        created.append({"question_instance_id": qi.id, "canonical_answer_id": answer.id,
                        "code": _entry_code(answer.slug)})

    db.session.commit()
    return jsonify({
        "diet": {"id": diet.id, "label": diet.label},
        "created": created,
        "count": len(created),
    }), 201


@bp.post("/parse-pdf")
@admin_required
def parse_pdf():
    """Extract a sitting date + questions from an uploaded exam-paper PDF for review.
    Writes nothing — the admin reviews/edits in the staging UI, then commits via
    POST /questions."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "no file uploaded"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "please upload a PDF file"}), 400
    head = file.stream.read(5)
    file.stream.seek(0)
    if head[:4] != b"%PDF":
        return jsonify({"error": "that does not look like a valid PDF"}), 400
    return jsonify(parse_exam_pdf(file.stream))
