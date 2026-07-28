"""Admin Add-Diet tool: entry listing, manual/batch question add, and PDF parsing."""
import io

import fitz  # PyMuPDF, used only to synthesise a test exam-paper PDF


def _make_pdf(lines):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for ln in lines:
        page.insert_text((72, y), ln)
        y += 24
    data = doc.tobytes()
    doc.close()
    return data


def test_add_diet_requires_admin(approved, content):
    assert approved.get("/api/admin/entries?subject=ek-motor").status_code == 403
    assert approved.post("/api/admin/questions", json={}).status_code == 403
    assert approved.post("/api/admin/parse-pdf").status_code == 403


def test_list_entries(admin, content):
    data = admin.get("/api/admin/entries?subject=ek-motor").get_json()
    assert data["subject"]["slug"] == "ek-motor"
    # the fixture's fuel answer is listed as a mappable entry
    assert any(e["canonical_answer_id"] == content["fuel_answer_id"] for e in data["entries"])


def test_manual_add_to_existing_entry_appears_in_index(admin, content):
    """Mapping a new sitting to an existing entry creates the diet + occurrence and it
    shows in the subject index immediately (no restart)."""
    resp = admin.post("/api/admin/questions", json={
        "subject_slug": "ek-motor", "month": 10, "year": 2026,
        "items": [{
            "question_number": "Q12", "wording": "A future fuel question. (10)",
            "canonical_answer_id": content["fuel_answer_id"],
        }],
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["count"] == 1
    assert body["diet"]["label"] in ("Oct 2026", "October 2026")

    index = admin.get("/api/subjects/ek-motor/index").get_json()["entries"]
    assert index[0]["sitting"] == body["diet"]["label"]  # future diet sorts first
    assert index[0]["q"] == "12"


def test_manual_add_new_entry_is_pending(admin, content):
    resp = admin.post("/api/admin/questions", json={
        "subject_slug": "ek-motor", "month": 12, "year": 2026,
        "items": [{
            "question_number": "Q13", "wording": "A brand-new topic question. (10)",
            "new_entry_title": "Brand new topic",
        }],
    })
    assert resp.status_code == 201
    aid = resp.get_json()["created"][0]["canonical_answer_id"]
    answer = admin.get(f"/api/answers/{aid}").get_json()
    assert answer["title"] == "Brand new topic"
    assert answer["answer_pending"] is True                 # no answer text yet
    assert answer["question_as_set"] == "A brand-new topic question. (10)"


def test_add_questions_validation(admin, content):
    base = {"subject_slug": "ek-motor", "month": 10, "year": 2026}
    assert admin.post("/api/admin/questions", json={**base, "items": []}).status_code == 400
    assert admin.post("/api/admin/questions",
                      json={**base, "month": 13, "items": [{"wording": "x", "new_entry_title": "t"}]}
                      ).status_code == 400
    # item mapped to neither an existing entry nor a new title
    assert admin.post("/api/admin/questions",
                      json={**base, "items": [{"wording": "x"}]}).status_code == 400
    assert admin.post("/api/admin/questions",
                      json={**base, "subject_slug": "nope", "items": [{"wording": "x", "new_entry_title": "t"}]}
                      ).status_code == 404


def test_parse_pdf_rejects_non_pdf(admin, content):
    resp = admin.post(
        "/api/admin/parse-pdf",
        data={"file": (io.BytesIO(b"not a pdf"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_parse_pdf_extracts_date_and_questions(admin, content):
    pdf = _make_pdf([
        "MCA / SQA Examination — July 2026",
        "Section C — Naval Architecture",
        "12. Describe the in-water survey of a very large carrier. (10)",
        "13. Explain the conditions of assignment of load line. (10)",
    ])
    resp = admin.post(
        "/api/admin/parse-pdf",
        data={"file": (io.BytesIO(pdf), "paper.pdf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert (data["month"], data["year"]) == (7, 2026)
    assert data["diet_label"] == "Jul 2026"
    numbers = {q["number"] for q in data["questions"]}
    assert {"Q12", "Q13"} <= numbers
