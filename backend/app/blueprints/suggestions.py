"""User-facing suggested-edit submission (spec 4.2, steps 1-2).

An approved member proposes improved answer text for a canonical answer, optionally
with sketch images. This writes a `pending` row (+ `suggested_edit_sketches`); the live
answer is untouched until an admin approves it (step 7).
"""
from flask import Blueprint, jsonify, request

from ..auth import approved_required, current_user
from ..extensions import db
from ..models import CanonicalAnswer, SuggestedEdit, SuggestedEditSketch
from ..services.storage import (
    MAX_UPLOAD_BYTES,
    StorageError,
    extension_ok,
    upload_fileobj,
)

bp = Blueprint("suggestions", __name__, url_prefix="/api")


def _file_size(fileobj) -> int:
    fileobj.stream.seek(0, 2)
    size = fileobj.stream.tell()
    fileobj.stream.seek(0)
    return size


@bp.post("/answers/<int:answer_id>/suggestions")
@approved_required
def submit_suggestion(answer_id):
    # Suggestions attach to the canonical answer, not a single question instance.
    answer = db.get_or_404(CanonicalAnswer, answer_id)

    # Accept JSON (text only) or multipart/form-data (text + sketch files).
    if request.files:
        text = (request.form.get("suggested_text") or "").strip()
        files = [f for f in request.files.getlist("sketches") if f and f.filename]
    else:
        data = request.get_json(silent=True) or {}
        text = (data.get("suggested_text") or "").strip()
        files = []

    if not text:
        return jsonify({"error": "suggested_text is required"}), 400

    # Validate all files up front, before uploading any.
    for f in files:
        if not extension_ok(f.filename):
            return jsonify({"error": f"unsupported file type: {f.filename}"}), 400
        if _file_size(f) > MAX_UPLOAD_BYTES:
            return jsonify({"error": f"{f.filename} exceeds the 5 MB limit"}), 400

    suggestion = SuggestedEdit(
        canonical_answer_id=answer.id,
        submitted_by_user_id=current_user().id,
        suggested_text=text,
    )
    db.session.add(suggestion)
    db.session.flush()  # assign suggestion.id for the sketch rows

    try:
        for f in files:
            key = upload_fileobj(f.stream, f.filename, f.mimetype)
            db.session.add(
                SuggestedEditSketch(suggested_edit_id=suggestion.id, image_path=key)
            )
    except StorageError:
        db.session.rollback()
        return jsonify({"error": "sketch storage is unavailable; try again"}), 503

    db.session.commit()

    return jsonify(
        {
            "id": suggestion.id,
            "status": suggestion.status.value,
            "sketch_count": len(files),
            "message": "Thanks — your suggestion is pending review.",
        }
    ), 201
