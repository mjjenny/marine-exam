"""Read-only content routes: subjects, diets, questions, and the Oral flat list.

All routes require an approved account. Written subjects use the
subject -> diet -> question hierarchy; EK Oral uses a flat, filterable question list
(its question_instances have diet_id = NULL).
"""
import re

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import func

from ..auth import approved_required
from ..extensions import db
from ..models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic
from ..services.storage import StorageError, get_object

bp = Blueprint("content", __name__, url_prefix="/api")


# ── serializers ──────────────────────────────────────────
def _subject_has_diets(subject_id: int) -> bool:
    return db.session.execute(
        db.select(Diet.id).filter_by(subject_id=subject_id).limit(1)
    ).first() is not None


def _subject_json(
    subject: Subject, has_diets: bool | None = None, answer_count: int | None = None
) -> dict:
    if has_diets is None:
        has_diets = _subject_has_diets(subject.id)
    data = {
        "id": subject.id,
        "name": subject.name,
        "slug": subject.slug,
        "has_diets": has_diets,
        "is_oral": subject.is_oral,
    }
    if answer_count is not None:
        data["answer_count"] = answer_count  # distinct canonical answers (for progress %)
    return data


def _topic_json(topic: Topic) -> dict:
    return {"id": topic.id, "name": topic.name}


def _feedback_label(is_oral: bool) -> str:
    return "What Examiner Would Drill Into" if is_oral else "Examiner Feedback"


def _get_subject_or_404(slug: str) -> Subject:
    return db.first_or_404(db.select(Subject).filter_by(slug=slug))


def _diet_desc():
    """Latest-first diet ordering, robust to diets added in the future: order by the
    diet's actual date (the semantic chronological key), with the seed-assigned
    sort_order as a stable tiebreak. Any diet given a valid date sorts correctly with
    no manual bookkeeping; nulls sort last."""
    return (Diet.date.desc().nullslast(), Diet.sort_order.desc().nullslast())


def _answer_is_pending(text: str | None) -> bool:
    """True when an entry has no published answer yet — a brand-new question (e.g. a
    future diet mapped to a fresh entry) whose model answer hasn't been written. Covers
    both empty text and the importer's 'Answer pending …' placeholder."""
    return not text or not text.strip() or text.strip().lower().startswith("answer pending")


# ── subjects ─────────────────────────────────────────────
@bp.get("/subjects")
@approved_required
def list_subjects():
    subjects = db.session.execute(
        db.select(Subject).order_by(Subject.id)
    ).scalars().all()
    # which subjects have at least one diet (single grouped query)
    with_diets = {
        sid
        for (sid,) in db.session.execute(
            db.select(Diet.subject_id).distinct()
        ).all()
    }
    # distinct canonical-answer count per subject (drives the book progress ribbon)
    answer_counts = dict(
        db.session.execute(
            db.select(CanonicalAnswer.subject_id, func.count(CanonicalAnswer.id))
            .group_by(CanonicalAnswer.subject_id)
        ).all()
    )
    return jsonify(
        [
            _subject_json(
                s, has_diets=s.id in with_diets, answer_count=answer_counts.get(s.id, 0)
            )
            for s in subjects
        ]
    )


@bp.get("/subjects/<slug>")
@approved_required
def get_subject(slug):
    subject = _get_subject_or_404(slug)
    topics = db.session.execute(
        db.select(Topic).filter_by(subject_id=subject.id).order_by(Topic.name)
    ).scalars().all()
    data = _subject_json(subject)
    data["topics"] = [_topic_json(t) for t in topics]
    return jsonify(data)


# ── whole-subject flat index (powers the homepage book index) ──
_INDEX_STATUS = {
    "verified_catalog": "Verified",
    "confirmed_via_screenshot_repeat_history": "Screenshot",
    "pre_catalog_or_unverified": "Unverified",
}
_ENTRY_CODE = re.compile(r"^e\d+$")


def _index_status(slug: str, source: str | None) -> str:
    """Entry-code catalogues (EK Naval: slug 'e39') show the code itself as status;
    other subjects fall back to the source-derived label."""
    if slug and _ENTRY_CODE.match(slug):
        return slug.upper()
    return _INDEX_STATUS.get(source, source or "—")


def _snippet(text: str | None, n: int = 80) -> str | None:
    """One-line preview of the verbatim question for the index subtitle."""
    if not text:
        return None
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= n else flat[:n].rstrip() + "…"


@bp.get("/subjects/<slug>/index")
@approved_required
def subject_index(slug):
    """Flat index of every question in the subject — one entry per sitting occurrence,
    plus any zero-occurrence reference answers. Shape: {sitting, q, question, status}."""
    subject = _get_subject_or_404(slug)
    order = ((QuestionInstance.id,) if subject.is_oral  # oral: keep bank order (Q1..Q694)
             else (*_diet_desc(), QuestionInstance.question_number, QuestionInstance.id))
    rows = db.session.execute(
        db.select(
            QuestionInstance, Diet, CanonicalAnswer.title, CanonicalAnswer.slug,
            CanonicalAnswer.question_as_set, CanonicalAnswer.answer_text,
        )
        .join(CanonicalAnswer, QuestionInstance.canonical_answer_id == CanonicalAnswer.id)
        .outerjoin(Diet, QuestionInstance.diet_id == Diet.id)
        .where(CanonicalAnswer.subject_id == subject.id)
        .order_by(*order)
    ).all()
    if subject.is_oral:
        # flat oral bank: each row is the individual verbatim question; it routes to a
        # shared master answer (subtitle = its topic) or, for ungrouped ones, a pending
        # entry. No sittings/entry-codes — the frontend hides the Sitting column.
        entries = [
            {
                "question_instance_id": qi.id,
                "canonical_answer_id": qi.canonical_answer_id,
                "sitting": None,
                "q": (qi.question_number or "").lstrip("Qq") or None,
                "question": qi.question_text_as_asked,
                "subtitle": None,
                "status": qi.source or ("Pending" if _answer_is_pending(answer_text) else ""),
            }
            for qi, diet, title, ca_slug, qas, answer_text in rows
        ]
    else:
        entries = [
            {
                "question_instance_id": qi.id,
                "canonical_answer_id": qi.canonical_answer_id,
                "sitting": diet.label if diet else None,
                "q": (qi.question_number or "").lstrip("Qq") or None,
                "question": title or qi.question_text_as_asked,
                "subtitle": _snippet(qas),  # verbatim-question preview under the title
                "status": _index_status(ca_slug, qi.source),
            }
            for qi, diet, title, ca_slug, qas, answer_text in rows
        ]
    # zero-occurrence reference answers have no sitting but still index-worthy
    zero = db.session.execute(
        db.select(CanonicalAnswer)
        .where(
            CanonicalAnswer.subject_id == subject.id,
            ~db.select(QuestionInstance.id)
            .where(QuestionInstance.canonical_answer_id == CanonicalAnswer.id)
            .exists(),
        )
        .order_by(CanonicalAnswer.id)
    ).scalars().all()
    for a in zero:
        entries.append(
            {
                "question_instance_id": None,
                "canonical_answer_id": a.id,
                "sitting": None,
                "q": None,
                "question": a.title or "(untitled)",
                "subtitle": _snippet(a.question_as_set),
                "status": a.slug.upper() if a.slug and _ENTRY_CODE.match(a.slug) else "Reference",
            }
        )
    return jsonify({"subject": _subject_json(subject), "entries": entries})


# ── diets (written subjects) ─────────────────────────────
@bp.get("/subjects/<slug>/diets")
@approved_required
def list_diets(slug):
    subject = _get_subject_or_404(slug)
    # question counts per diet, in one grouped query
    counts = dict(
        db.session.execute(
            db.select(QuestionInstance.diet_id, func.count(QuestionInstance.id))
            .group_by(QuestionInstance.diet_id)
        ).all()
    )
    diets = db.session.execute(
        db.select(Diet)
        .filter_by(subject_id=subject.id)
        .order_by(*_diet_desc())
    ).scalars().all()
    return jsonify(
        [
            {
                "id": d.id,
                "label": d.label,
                "date": d.date.isoformat() if d.date else None,
                "question_count": counts.get(d.id, 0),
            }
            for d in diets
        ]
    )


def _occurrences_by_answer(answer_ids):
    """{canonical_answer_id: [occurrence]} for every occurrence, latest diet first.
    Each occurrence: {question_instance_id, diet_label, question_text, sort_order}."""
    if not answer_ids:
        return {}
    rows = db.session.execute(
        db.select(
            QuestionInstance.canonical_answer_id,
            QuestionInstance.id,
            QuestionInstance.question_text_as_asked,
            Diet.label,
            Diet.sort_order,
        )
        .outerjoin(Diet, QuestionInstance.diet_id == Diet.id)
        .where(QuestionInstance.canonical_answer_id.in_(answer_ids))
        .order_by(*_diet_desc(), QuestionInstance.id)
    ).all()
    out = {}
    for caid, qi_id, qtext, label, order in rows:
        out.setdefault(caid, []).append(
            {"question_instance_id": qi_id, "diet_label": label,
             "question_text": qtext, "sort_order": order}
        )
    return out


def _distinct_diets(occurrences):
    """Ordered {diet_label: representative question_instance_id}, latest first."""
    seen = {}
    for o in occurrences:
        if o["diet_label"] and o["diet_label"] not in seen:
            seen[o["diet_label"]] = o["question_instance_id"]
    return seen


@bp.get("/diets/<int:diet_id>")
@approved_required
def get_diet(diet_id):
    diet = db.get_or_404(Diet, diet_id)
    subject = db.session.get(Subject, diet.subject_id)
    rows = db.session.execute(
        db.select(QuestionInstance, Topic.name)
        .join(CanonicalAnswer, QuestionInstance.canonical_answer_id == CanonicalAnswer.id)
        .outerjoin(Topic, CanonicalAnswer.topic_id == Topic.id)
        .where(QuestionInstance.diet_id == diet_id)
        .order_by(QuestionInstance.question_number, QuestionInstance.id)
    ).all()
    # repeat-history: which other diets each question also appeared in
    occ = _occurrences_by_answer([qi.canonical_answer_id for qi, _ in rows])
    questions = []
    for qi, topic_name in rows:
        diet_labels = list(_distinct_diets(occ.get(qi.canonical_answer_id, [])).keys())
        questions.append(
            {
                "id": qi.id,
                "question_number": qi.question_number,
                "question_text_as_asked": qi.question_text_as_asked,
                "topic_name": topic_name,
                "repeat_count": len(diet_labels),
                "repeat_diets": diet_labels,  # all diets (incl. this one), latest first
            }
        )
    return jsonify(
        {
            "id": diet.id,
            "label": diet.label,
            "date": diet.date.isoformat() if diet.date else None,
            "subject": _subject_json(subject),
            "questions": questions,
        }
    )


# ── topic view (one row per question, with cross-diet repeat history) ──
@bp.get("/topics/<int:topic_id>/questions")
@approved_required
def list_topic_questions(topic_id):
    topic = db.get_or_404(Topic, topic_id)
    subject = db.session.get(Subject, topic.subject_id)
    answers = db.session.execute(
        db.select(CanonicalAnswer).where(CanonicalAnswer.topic_id == topic_id)
    ).scalars().all()
    occ = _occurrences_by_answer([a.id for a in answers])

    # One row per canonical answer, listing every diet it appeared in (repeat history).
    questions = []
    for a in answers:
        rows_a = occ.get(a.id, [])
        diets = _distinct_diets(rows_a)  # {label: qi_id}, latest first
        rep = rows_a[0] if rows_a else None
        questions.append(
            {
                "canonical_answer_id": a.id,
                # representative (latest) occurrence to open; None -> link to answer page
                "question_instance_id": rep["question_instance_id"] if rep else None,
                "question_text_as_asked": (rep["question_text"] if rep else None)
                or a.title
                or "(untitled)",
                "repeat_count": len(diets),
                "repeat_diets": list(diets.keys()),
                "_sort": rep["sort_order"] if rep and rep["sort_order"] is not None else -1,
            }
        )
    # High-repeat / most-recent first; zero-occurrence reference rows last.
    questions.sort(key=lambda q: (q["repeat_count"], q["_sort"]), reverse=True)
    for q in questions:
        q.pop("_sort")

    return jsonify(
        {
            "topic": {
                "id": topic.id,
                "name": topic.name,
                "subject": _subject_json(subject),
            },
            "questions": questions,
        }
    )


# ── single canonical answer (viewable even with zero occurrences) ──
@bp.get("/answers/<int:answer_id>")
@approved_required
def get_answer(answer_id):
    answer = db.get_or_404(CanonicalAnswer, answer_id)
    subject = db.session.get(Subject, answer.subject_id)
    topic = db.session.get(Topic, answer.topic_id) if answer.topic_id else None
    occ = db.session.execute(
        db.select(QuestionInstance, Diet)
        .outerjoin(Diet, QuestionInstance.diet_id == Diet.id)
        .where(QuestionInstance.canonical_answer_id == answer.id)
        .order_by(*_diet_desc(), QuestionInstance.id)
    ).all()
    return jsonify(
        {
            "id": answer.id,
            "title": answer.title,
            "question_as_set": answer.question_as_set,
            "answer_text": answer.answer_text,
            "answer_pending": _answer_is_pending(answer.answer_text),
            "sketch_refs": answer.sketch_refs or [],
            "subject": _subject_json(subject),
            "topic": _topic_json(topic) if topic else None,
            "occurrences": [
                {
                    "question_instance_id": qi.id,
                    "diet_id": d.id if d else None,
                    "diet_label": d.label if d else None,
                    "question_number": qi.question_number,
                }
                for qi, d in occ
            ],
        }
    )


# ── flat question list (EK Oral; works for any subject) ──
@bp.get("/subjects/<slug>/questions")
@approved_required
def list_subject_questions(slug):
    subject = _get_subject_or_404(slug)
    topic_id = request.args.get("topic_id", type=int)
    search = (request.args.get("q") or "").strip()

    stmt = (
        db.select(QuestionInstance, Topic.name)
        .join(CanonicalAnswer, QuestionInstance.canonical_answer_id == CanonicalAnswer.id)
        .outerjoin(Topic, CanonicalAnswer.topic_id == Topic.id)
        .where(CanonicalAnswer.subject_id == subject.id)
    )
    if topic_id is not None:
        stmt = stmt.where(CanonicalAnswer.topic_id == topic_id)
    if search:
        stmt = stmt.where(QuestionInstance.question_text_as_asked.ilike(f"%{search}%"))
    stmt = stmt.order_by(QuestionInstance.id)

    rows = db.session.execute(stmt).all()
    return jsonify(
        {
            "subject": _subject_json(subject),
            "questions": [
                {
                    "id": qi.id,
                    "question_text_as_asked": qi.question_text_as_asked,
                    "topic_name": topic_name,
                }
                for qi, topic_name in rows
            ],
        }
    )


# ── sketch images (gated proxy to object storage) ───────
@bp.get("/sketches/<path:key>")
@approved_required
def get_sketch(key):
    """Stream a stored sketch image. Access-controlled so only approved members
    can view images; the storage endpoint/credentials never reach the browser."""
    try:
        body, content_type = get_object(key)
    except StorageError:
        return jsonify({"error": "sketch not found"}), 404
    return Response(
        body.iter_chunks(),
        content_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


# ── single question page ─────────────────────────────────
@bp.get("/questions/<int:question_id>")
@approved_required
def get_question(question_id):
    qi = db.get_or_404(QuestionInstance, question_id)
    answer = db.session.get(CanonicalAnswer, qi.canonical_answer_id)
    subject = db.session.get(Subject, answer.subject_id)
    topic = db.session.get(Topic, answer.topic_id) if answer.topic_id else None
    diet = db.session.get(Diet, qi.diet_id) if qi.diet_id else None
    is_oral = diet is None

    # "Also asked in": other instances of the same canonical answer that have a diet.
    also_rows = db.session.execute(
        db.select(QuestionInstance, Diet)
        .join(Diet, QuestionInstance.diet_id == Diet.id)
        .where(QuestionInstance.canonical_answer_id == qi.canonical_answer_id)
        .where(QuestionInstance.id != qi.id)
        .order_by(*_diet_desc())
    ).all()

    return jsonify(
        {
            "id": qi.id,
            "question_number": qi.question_number,
            "question_text_as_asked": qi.question_text_as_asked,
            "examiner_feedback_text": qi.examiner_feedback_text,
            "feedback_label": _feedback_label(is_oral),
            "subject": _subject_json(subject),
            "diet": {"id": diet.id, "label": diet.label} if diet else None,
            "topic": _topic_json(topic) if topic else None,
            "canonical_answer": {
                "id": answer.id,
                "title": answer.title,
                "question_as_set": answer.question_as_set,
                "answer_text": answer.answer_text,
                "answer_pending": _answer_is_pending(answer.answer_text),
                "sketch_refs": answer.sketch_refs or [],
            },
            "also_asked_in": [
                {
                    "question_instance_id": other.id,
                    "diet_id": d.id,
                    "diet_label": d.label,
                    "date": d.date.isoformat() if d.date else None,
                }
                for other, d in also_rows
            ],
        }
    )
