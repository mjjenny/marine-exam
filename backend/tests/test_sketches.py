"""Sketch upload, gated serving, and promotion to the canonical answer on approval.

Uses the `fake_storage` fixture (in-process stand-in) so MinIO isn't required.
"""
from app.extensions import db
from app.models import CanonicalAnswer, SuggestedEditSketch

from .helpers import png_upload


def _submit_with_sketch(client, answer_id, text="With a diagram.", name="sketch.png"):
    return client.post(
        f"/api/answers/{answer_id}/suggestions",
        data={"suggested_text": text, "sketches": png_upload(name)},
        content_type="multipart/form-data",
    )


def test_upload_sketch_creates_row(approved, app, content, fake_storage):
    resp = _submit_with_sketch(approved, content["fuel_answer_id"])
    assert resp.status_code == 201
    assert resp.get_json()["sketch_count"] == 1
    with app.app_context():
        n = db.session.scalar(db.select(db.func.count(SuggestedEditSketch.id)))
    assert n == 1
    assert len(fake_storage) == 1  # one object stored


def test_upload_rejects_bad_file_type(approved, content, fake_storage):
    resp = approved.post(
        f"/api/answers/{content['fuel_answer_id']}/suggestions",
        data={"suggested_text": "x", "sketches": png_upload("notes.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_serve_sketch_requires_auth(approved, anon, content, fake_storage):
    _submit_with_sketch(approved, content["fuel_answer_id"])
    key = next(iter(fake_storage))
    assert anon.get(f"/api/sketches/{key}").status_code == 401


def test_serve_sketch_returns_bytes(approved, content, fake_storage):
    _submit_with_sketch(approved, content["fuel_answer_id"])
    key = next(iter(fake_storage))
    resp = approved.get(f"/api/sketches/{key}")
    assert resp.status_code == 200
    assert resp.data == fake_storage[key][0]


def test_serve_missing_sketch_404(approved, fake_storage):
    assert approved.get("/api/sketches/sketches/does-not-exist.png").status_code == 404


def test_approve_promotes_sketch_to_answer(admin, approved, app, content, fake_storage):
    resp = _submit_with_sketch(approved, content["fuel_answer_id"])
    sid = resp.get_json()["id"]

    approve = admin.post(f"/api/admin/suggestions/{sid}/approve", json={})
    assert approve.get_json()["promoted_sketches"] == 1

    with app.app_context():
        refs = db.session.get(CanonicalAnswer, content["fuel_answer_id"]).sketch_refs
    assert len(refs) == 1
    assert refs[0]["path"] in fake_storage
