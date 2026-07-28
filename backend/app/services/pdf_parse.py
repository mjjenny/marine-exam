"""Best-effort exam-paper PDF parser (Method B of the admin "Add Diet" tool).

Uses the same pdfplumber text-extraction + question-cleaning approach as the EK Naval
seed parser, generalised to an arbitrary MCA/SQA exam paper: it pulls the sitting date
and the numbered questions so the admin can review/correct them in a staging UI before
anything is written to the database. Parsing is heuristic by design — the staging step
is the safety net, and rows are fully editable there.
"""
import re

import pdfplumber

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

_MONTH_RE = re.compile(
    r"\b(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?\s+(20\d{2})\b",
    re.IGNORECASE,
)
_QNUM_RE = re.compile(r"^\s*(?:Q(?:uestion)?\s*)?(\d{1,2})[.)]\s+(.*)", re.IGNORECASE)
_FOOTER_RE = re.compile(r"(?im)^.*(page \d+ of \d+|section [abc]\b).*$")


def _find_date(text):
    """First 'Month YYYY' in the document — the sitting date. Returns (month, year, label)."""
    m = _MONTH_RE.search(text)
    if not m:
        return None, None, None
    month = _MONTHS[m.group(1).lower()]
    year = int(m.group(2))
    return month, year, f"{_ABBR[month]} {year}"


def _clean(wording):
    return re.sub(r"\s+", " ", wording).strip()


def _find_questions(text):
    """Split into numbered questions. Each becomes {number, wording}; sub-parts
    (a)/(b) and marks stay within the question they belong to."""
    out, cur = [], None
    for raw in text.split("\n"):
        line = _FOOTER_RE.sub("", raw)
        m = _QNUM_RE.match(line)
        if m and 1 <= int(m.group(1)) <= 30:
            if cur:
                out.append(cur)
            cur = {"number": f"Q{int(m.group(1))}", "wording": m.group(2).strip()}
        elif cur is not None and line.strip():
            cur["wording"] += " " + line.strip()
    if cur:
        out.append(cur)
    # keep only substantive questions; tidy whitespace
    cleaned = []
    for q in out:
        w = _clean(q["wording"])
        if len(w) >= 15 and re.search(r"[a-z]", w):
            cleaned.append({"number": q["number"], "wording": w})
    return cleaned


def parse_exam_pdf(fileobj):
    """Parse an exam-paper PDF into {month, year, diet_label, questions, warning?}.
    Never raises on a malformed paper — returns a warning instead so the admin can
    still enter data manually in the staging UI."""
    try:
        with pdfplumber.open(fileobj) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as exc:  # noqa: BLE001 — surface any pdf error to the admin
        return {"month": None, "year": None, "diet_label": None, "questions": [],
                "warning": f"Could not read the PDF: {exc}"}

    month, year, label = _find_date(text)
    questions = _find_questions(text)
    warning = None
    if not questions:
        warning = "No questions could be detected automatically — add them manually below."
    elif not label:
        warning = "Could not detect the sitting date — please set it manually."
    return {"month": month, "year": year, "diet_label": label,
            "questions": questions, "warning": warning}
