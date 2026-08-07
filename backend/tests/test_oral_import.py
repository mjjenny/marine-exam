"""EK Oral PDF import: parsing + idempotent DB insertion."""
import fitz  # PyMuPDF
import pytest

from app.extensions import db
from app.models import CanonicalAnswer, QuestionInstance, Subject
from app.services.oral_import import (
    PDFParseError,
    import_oral_pdf,
    parse_qa_blocks,
)

SAMPLE = """Chapter 1: Role and Handover
Q1. What was your last ship type and engine? A: A Capesize bulk carrier with a
MAN B&W 6S60MC-C two-stroke main engine.
Q2. How would you take over as Chief Engineer? A: Review the Engine Room Log,
PMS status, running hours, and outstanding defects, then walk the engine room.
Chapter 2: Safety Management
Q3. What is the ISM Code? A: The International Safety Management Code for the safe
operation of ships and pollution prevention.
"""


def _write_pdf(path, text):
    doc = fitz.open()
    page = doc.new_page()
    # Text box wide/tall enough that nothing is clipped out of the extracted text.
    page.insert_textbox(fitz.Rect(36, 36, 560, 780), text, fontsize=11)
    doc.save(str(path))
    doc.close()


def test_parse_qa_blocks_splits_questions_and_answers():
    blocks = parse_qa_blocks(SAMPLE)
    assert len(blocks) == 3
    assert blocks[0]["number"] == "Q1"
    assert blocks[0]["question"].startswith("What was your last ship")
    assert "MAN B&W" in blocks[0]["answer"]
    # A chapter heading between Q2 and Q3 must not leak into Q2's answer.
    assert "Chapter 2" not in blocks[1]["answer"]
    assert blocks[2]["question"] == "What is the ISM Code?"


def test_parse_handles_missing_answer_marker():
    blocks = parse_qa_blocks("Q1. A question with no answer marker here\n")
    assert len(blocks) == 1
    assert blocks[0]["answer"] == ""
    assert blocks[0]["question"].startswith("A question with no answer")


def test_import_creates_oral_subject_and_entries(app, tmp_path):
    pdf = tmp_path / "orals.pdf"
    _write_pdf(pdf, SAMPLE)

    with app.app_context():
        summary = import_oral_pdf(str(pdf))
        assert summary["imported"] == 3
        assert summary["parsed"] == 3
        assert summary["skipped"] == 0

        subject = db.session.execute(
            db.select(Subject).filter_by(slug="ek-oral")
        ).scalar_one()
        assert subject.is_oral is True

        answers = db.session.execute(
            db.select(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id)
        ).scalars().all()
        assert len(answers) == 3
        # Flat oral shape: no topic, no diet, question stored verbatim as the set question.
        assert all(a.topic_id is None for a in answers)
        assert all(a.question_as_set for a in answers)

        instances = db.session.execute(db.select(QuestionInstance)).scalars().all()
        assert len(instances) == 3
        assert all(qi.diet_id is None for qi in instances)
        assert all(qi.source == "Oral PDF Import" for qi in instances)


def test_import_is_idempotent(app, tmp_path):
    pdf = tmp_path / "orals.pdf"
    _write_pdf(pdf, SAMPLE)

    with app.app_context():
        first = import_oral_pdf(str(pdf))
        assert first["imported"] == 3

        # Re-importing the same PDF adds nothing.
        second = import_oral_pdf(str(pdf))
        assert second["imported"] == 0
        assert second["skipped"] == 3

        count = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id)))
        assert count == 3


def test_import_rejects_pdf_with_no_questions(app, tmp_path):
    pdf = tmp_path / "empty.pdf"
    _write_pdf(pdf, "This document has no question markers at all.\nJust prose.")

    with app.app_context():
        with pytest.raises(PDFParseError):
            import_oral_pdf(str(pdf))


def test_import_missing_file_raises(app):
    with app.app_context():
        with pytest.raises(PDFParseError):
            import_oral_pdf("does-not-exist.pdf")
