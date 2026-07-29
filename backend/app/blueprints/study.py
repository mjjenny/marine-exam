"""Student study QoL: progress tracking and bookmarks."""
from flask import Blueprint, jsonify, request

from ..auth import approved_required, current_user
from ..extensions import db
from ..models import Bookmark, UserProgress
from ..models.study import CONTENT_TYPES

bp = Blueprint("study", __name__, url_prefix="/api")


def _parse_content_ref(data: dict):
    content_type = (data.get("content_type") or "").strip().lower()
    content_id = data.get("content_id")
    if content_type not in CONTENT_TYPES:
        return None, None, (jsonify({"error": "invalid content_type"}), 400)
    try:
        content_id = int(content_id)
    except (TypeError, ValueError):
        return None, None, (jsonify({"error": "content_id must be an integer"}), 400)
    if content_id < 1:
        return None, None, (jsonify({"error": "content_id must be positive"}), 400)
    return content_type, content_id, None


def _progress_json(row: UserProgress) -> dict:
    return {
        "id": row.id,
        "content_type": row.content_type,
        "content_id": row.content_id,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _bookmark_json(row: Bookmark) -> dict:
    return {
        "id": row.id,
        "content_type": row.content_type,
        "content_id": row.content_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@bp.get("/progress/summary")
@approved_required
def progress_summary():
    """Per-subject completion stats for the student dashboard."""
    from ..models import CanonicalAnswer, Subject

    user = current_user()
    subjects = db.session.execute(db.select(Subject).order_by(Subject.id)).scalars().all()
    totals = dict(
        db.session.execute(
            db.select(CanonicalAnswer.subject_id, db.func.count(CanonicalAnswer.id)).group_by(
                CanonicalAnswer.subject_id
            )
        ).all()
    )
    completed_rows = db.session.execute(
        db.select(UserProgress.content_id).where(
            UserProgress.user_id == user.id,
            UserProgress.content_type == "answer",
        )
    ).scalars().all()
    completed_ids = set(completed_rows)

    # Map answer id -> subject id for completed answers only.
    completed_by_subject = {}
    if completed_ids:
        for sid, aid in db.session.execute(
            db.select(CanonicalAnswer.subject_id, CanonicalAnswer.id).where(
                CanonicalAnswer.id.in_(completed_ids)
            )
        ).all():
            completed_by_subject[sid] = completed_by_subject.get(sid, 0) + 1

    out = []
    for s in subjects:
        total = int(totals.get(s.id, 0))
        done = int(completed_by_subject.get(s.id, 0))
        pct = round((done / total) * 100) if total else 0
        out.append(
            {
                "subject_id": s.id,
                "slug": s.slug,
                "name": s.name,
                "completed": done,
                "total": total,
                "percent": pct,
            }
        )
    return jsonify(out)


@bp.get("/progress")
@approved_required
def list_progress():
    """Return the current user's completed items (optionally filtered)."""
    user = current_user()
    content_type = (request.args.get("content_type") or "").strip().lower() or None
    stmt = db.select(UserProgress).where(UserProgress.user_id == user.id)
    if content_type:
        if content_type not in CONTENT_TYPES:
            return jsonify({"error": "invalid content_type"}), 400
        stmt = stmt.where(UserProgress.content_type == content_type)
    stmt = stmt.order_by(UserProgress.completed_at.desc())
    rows = db.session.execute(stmt).scalars().all()
    return jsonify([_progress_json(r) for r in rows])


@bp.post("/progress/toggle")
@approved_required
def toggle_progress():
    """Mark content complete, or clear completion if already marked."""
    user = current_user()
    data = request.get_json(silent=True) or {}
    content_type, content_id, err = _parse_content_ref(data)
    if err:
        return err

    existing = db.session.execute(
        db.select(UserProgress).where(
            UserProgress.user_id == user.id,
            UserProgress.content_type == content_type,
            UserProgress.content_id == content_id,
        )
    ).scalar_one_or_none()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify(
            {
                "completed": False,
                "content_type": content_type,
                "content_id": content_id,
            }
        )

    row = UserProgress(
        user_id=user.id, content_type=content_type, content_id=content_id
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(
        {
            "completed": True,
            "content_type": content_type,
            "content_id": content_id,
            "item": _progress_json(row),
        }
    )


@bp.get("/bookmarks")
@approved_required
def list_bookmarks():
    user = current_user()
    content_type = (request.args.get("content_type") or "").strip().lower() or None
    stmt = db.select(Bookmark).where(Bookmark.user_id == user.id)
    if content_type:
        if content_type not in CONTENT_TYPES:
            return jsonify({"error": "invalid content_type"}), 400
        stmt = stmt.where(Bookmark.content_type == content_type)
    stmt = stmt.order_by(Bookmark.created_at.desc())
    rows = db.session.execute(stmt).scalars().all()
    return jsonify([_bookmark_json(r) for r in rows])


@bp.post("/bookmarks/toggle")
@approved_required
def toggle_bookmark():
    user = current_user()
    data = request.get_json(silent=True) or {}
    content_type, content_id, err = _parse_content_ref(data)
    if err:
        return err

    existing = db.session.execute(
        db.select(Bookmark).where(
            Bookmark.user_id == user.id,
            Bookmark.content_type == content_type,
            Bookmark.content_id == content_id,
        )
    ).scalar_one_or_none()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify(
            {
                "bookmarked": False,
                "content_type": content_type,
                "content_id": content_id,
            }
        )

    row = Bookmark(user_id=user.id, content_type=content_type, content_id=content_id)
    db.session.add(row)
    db.session.commit()
    return jsonify(
        {
            "bookmarked": True,
            "content_type": content_type,
            "content_id": content_id,
            "item": _bookmark_json(row),
        }
    )
