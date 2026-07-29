"""Progress and bookmark API ownership + toggle behaviour."""


def test_progress_requires_auth(anon):
    assert anon.get("/api/progress").status_code == 401
    assert anon.post(
        "/api/progress/toggle", json={"content_type": "answer", "content_id": 1}
    ).status_code == 401


def test_bookmarks_require_auth(anon):
    assert anon.get("/api/bookmarks").status_code == 401
    assert anon.post(
        "/api/bookmarks/toggle", json={"content_type": "answer", "content_id": 1}
    ).status_code == 401


def test_progress_requires_approved(pending):
    assert pending.get("/api/progress").status_code == 403


def test_toggle_progress_round_trip(approved, content):
    aid = content["fuel_answer_id"]
    on = approved.post(
        "/api/progress/toggle",
        json={"content_type": "answer", "content_id": aid},
    )
    assert on.status_code == 200
    assert on.get_json()["completed"] is True

    listed = approved.get("/api/progress").get_json()
    assert any(i["content_id"] == aid and i["content_type"] == "answer" for i in listed)

    off = approved.post(
        "/api/progress/toggle",
        json={"content_type": "answer", "content_id": aid},
    )
    assert off.status_code == 200
    assert off.get_json()["completed"] is False
    listed2 = approved.get("/api/progress").get_json()
    assert not any(i["content_id"] == aid for i in listed2)


def test_users_only_see_own_progress(user_factory, login, content):
    aid = content["fuel_answer_id"]
    a = user_factory(status="approved", email="a@test.local")
    b = user_factory(status="approved", email="b@test.local")
    ca = login(a["email"], a["password"])
    cb = login(b["email"], b["password"])

    assert ca.post(
        "/api/progress/toggle",
        json={"content_type": "answer", "content_id": aid},
    ).status_code == 200

    assert len(ca.get("/api/progress").get_json()) == 1
    assert cb.get("/api/progress").get_json() == []


def test_toggle_bookmark_round_trip(approved, content):
    qid = content["qi_july_id"]
    on = approved.post(
        "/api/bookmarks/toggle",
        json={"content_type": "question", "content_id": qid},
    )
    assert on.status_code == 200
    assert on.get_json()["bookmarked"] is True
    assert any(
        i["content_id"] == qid for i in approved.get("/api/bookmarks").get_json()
    )

    off = approved.post(
        "/api/bookmarks/toggle",
        json={"content_type": "question", "content_id": qid},
    )
    assert off.get_json()["bookmarked"] is False


def test_users_only_see_own_bookmarks(user_factory, login, content):
    qid = content["qi_july_id"]
    a = user_factory(status="approved", email="ba@test.local")
    b = user_factory(status="approved", email="bb@test.local")
    ca = login(a["email"], a["password"])
    cb = login(b["email"], b["password"])

    assert ca.post(
        "/api/bookmarks/toggle",
        json={"content_type": "question", "content_id": qid},
    ).status_code == 200
    assert len(ca.get("/api/bookmarks").get_json()) == 1
    assert cb.get("/api/bookmarks").get_json() == []


def test_invalid_content_type_rejected(approved):
    resp = approved.post(
        "/api/progress/toggle",
        json={"content_type": "spaceship", "content_id": 1},
    )
    assert resp.status_code == 400


def test_progress_summary_shape(approved, content):
    aid = content["fuel_answer_id"]
    approved.post(
        "/api/progress/toggle",
        json={"content_type": "answer", "content_id": aid},
    )
    rows = approved.get("/api/progress/summary").get_json()
    assert isinstance(rows, list)
    motor = next(r for r in rows if r["slug"] == "ek-motor")
    assert motor["completed"] >= 1
    assert motor["total"] >= 1
    assert 0 <= motor["percent"] <= 100
