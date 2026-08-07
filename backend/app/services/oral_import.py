"""Import EK Oral questions & model answers from a PDF question bank.

Text is extracted with PyMuPDF (``import fitz``) and split into question/answer
blocks by the patterns below. Parsed blocks are inserted as flat EK Oral entries
(one ``CanonicalAnswer`` + one ``QuestionInstance`` each, ``diet_id`` = NULL), the
same shape the rest of EK Oral uses. Re-running with the same PDF is a no-op — each
entry is keyed by a content hash of its question, so nothing is duplicated.

Used by the ``flask import-orals <pdf>`` CLI command (see app/cli.py).

────────────────────────────────────────────────────────────────────────────
ADJUSTING THE PARSER FOR A DIFFERENT PDF LAYOUT
Only three regexes below decide how the text is cut up. If a new PDF doesn't
parse, tweak these — nothing else needs to change:

  • QUESTION_START — what marks the start of a question. Currently matches
        "Q1." / "Q42."   "Q:"   "Q)"   "Question 3:"   "Question:"
    e.g. for "1) ..." numbering use:  r"^\\s*(?P<num>\\d+)\\)\\s*"
  • ANSWER_MARKER  — what separates the question from its answer inside a block.
        Currently matches " A: ", " A. ", " Ans: ", " Answer: "
    e.g. for "Model Answer:" use:  r"(?:^|\\s)Model Answer\\s*[:.]\\s+"
  • CHAPTER        — section headings, used only as block boundaries so a
        question never swallows the next section's heading.
────────────────────────────────────────────────────────────────────────────
"""
import hashlib
import os
import re

import fitz  # PyMuPDF

from ..extensions import db
from ..models import CanonicalAnswer, QuestionInstance, Subject

ORAL_SLUG = "ek-oral"
ORAL_NAME = "EK Oral"
IMPORT_SOURCE = "Oral PDF Import"

# A question begins at a line starting with one of these markers. Case-insensitive.
QUESTION_START = re.compile(
    r"^\s*Q(?:uestion)?\s*(?P<num>\d+)?\s*[.:)]\s*",
    re.IGNORECASE | re.MULTILINE,
)
# Splits a block into (question, answer). Requires leading whitespace/line-start so a
# stray "A:" inside prose is unlikely to trigger a false split.
ANSWER_MARKER = re.compile(r"(?:^|\s)(?:A|Ans|Answer)\s*[.:)]\s+", re.IGNORECASE)
# Section headings ("Chapter 1: ...") — boundaries only, not stored (EK Oral is flat).
CHAPTER = re.compile(r"^\s*Chapter\s+\d+\s*:.*$", re.IGNORECASE | re.MULTILINE)


class PDFParseError(Exception):
    """Raised when the PDF can't be opened or yields no recognisable Q/A blocks."""


def _collapse_ws(text: str) -> str:
    """Flatten PDF line-wrapping into clean single-spaced text."""
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(path: str) -> str:
    """Return the full text of the PDF at ``path`` (all pages concatenated)."""
    if not os.path.exists(path):
        raise PDFParseError(f"PDF not found: {path}")
    try:
        doc = fitz.open(path)
    except Exception as exc:  # noqa: BLE001 — fitz raises a variety of low-level errors
        raise PDFParseError(f"Could not open PDF: {exc}") from exc
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def parse_qa_blocks(text: str) -> list[dict]:
    """Split extracted text into [{number, question, answer}] blocks.

    Each question runs from its marker to the next question marker; a chapter
    heading inside that span truncates it (so trailing section headings don't leak
    into an answer). The block is then split on the first answer marker.
    """
    starts = list(QUESTION_START.finditer(text))
    blocks: list[dict] = []
    for i, m in enumerate(starts):
        body_start = m.end()
        body_end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = text[body_start:body_end]

        # Cut the block at the first section heading it contains, if any.
        chap = CHAPTER.search(body)
        if chap:
            body = body[: chap.start()]

        split = ANSWER_MARKER.search(body)
        if split:
            question = _collapse_ws(body[: split.start()])
            answer = _collapse_ws(body[split.end():])
        else:
            question = _collapse_ws(body)
            answer = ""

        if not question:
            continue  # a bare marker with no text — skip

        num = m.group("num")
        blocks.append({
            "number": f"Q{num}" if num else None,
            "question": question,
            "answer": answer,
        })
    return blocks


def _question_slug(question: str) -> str:
    """Deterministic slug from the question text — makes imports idempotent."""
    norm = _collapse_ws(question).lower()
    return "oral-pdf-" + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def get_or_create_oral_subject() -> Subject:
    """Return the EK Oral subject, creating it (flat, is_oral=True) if absent."""
    subject = db.session.execute(
        db.select(Subject).filter_by(slug=ORAL_SLUG)
    ).scalar_one_or_none()
    if subject is None:
        subject = Subject(name=ORAL_NAME, slug=ORAL_SLUG, is_oral=True)
        db.session.add(subject)
        db.session.flush()
    return subject


def import_oral_pdf(path: str) -> dict:
    """Parse ``path`` and insert new EK Oral questions. Commits on success.

    Returns a summary dict: parsed / imported / skipped / no_answer. Raises
    PDFParseError if the PDF is unreadable or contains no Q/A blocks. The caller
    (CLI command) is responsible for rolling back on any exception.
    """
    text = extract_pdf_text(path)
    blocks = parse_qa_blocks(text)
    if not blocks:
        raise PDFParseError(
            "No question/answer blocks found. Check the PDF is text (not scanned "
            "images) and that its format matches the QUESTION_START / ANSWER_MARKER "
            "patterns in app/services/oral_import.py."
        )

    subject = get_or_create_oral_subject()

    # Slugs already in the DB for this subject — skip them so re-imports don't duplicate.
    existing = set(
        db.session.execute(
            db.select(CanonicalAnswer.slug).where(
                CanonicalAnswer.subject_id == subject.id,
                CanonicalAnswer.slug.is_not(None),
            )
        ).scalars().all()
    )

    imported = skipped = no_answer = 0
    seen: set[str] = set()
    for block in blocks:
        slug = _question_slug(block["question"])
        if slug in existing or slug in seen:  # duplicate across DB or within this PDF
            skipped += 1
            continue
        seen.add(slug)

        answer = CanonicalAnswer(
            subject_id=subject.id,
            topic_id=None,  # EK Oral is flat — no topic layer (matches existing entries)
            slug=slug,
            title=block["question"][:200],
            question_as_set=block["question"],
            answer_text=block["answer"] or "",
            sketch_refs=[],
        )
        db.session.add(answer)
        db.session.flush()  # assign answer.id for the FK below

        db.session.add(QuestionInstance(
            canonical_answer_id=answer.id,
            diet_id=None,  # oral rows never belong to a diet
            question_number=block["number"],
            question_text_as_asked=block["question"],
            examiner_feedback_text=None,
            source=IMPORT_SOURCE,
        ))
        imported += 1
        if not block["answer"]:
            no_answer += 1

    db.session.commit()
    return {
        "parsed": len(blocks),
        "imported": imported,
        "skipped": skipped,
        "no_answer": no_answer,
    }
