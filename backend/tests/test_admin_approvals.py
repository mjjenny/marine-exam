"""Admin member-approval queue."""


def test_approval_queue_requires_admin(approved):
    assert approved.get("/api/admin/users?status=pending").status_code == 403


def test_approval_queue_requires_auth(anon):
    assert anon.get("/api/admin/users").status_code == 401


def test_list_pending_users(admin, user_factory):
    user_factory(status="pending", email="p1@test.local")
    user_factory(status="pending", email="p2@test.local")
    users = admin.get("/api/admin/users?status=pending").get_json()
    emails = {u["email"] for u in users}
    assert {"p1@test.local", "p2@test.local"} <= emails
    assert admin.get("/api/admin/pending-count").get_json()["count"] >= 2


def test_approve_grants_content_access(admin, user_factory, login, content):
    u = user_factory(status="pending")
    # Before approval the member is blocked from content.
    member = login(u["email"], u["password"])
    assert member.get("/api/subjects").status_code == 403

    resp = admin.post(f"/api/admin/users/{u['id']}/approve")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "approved"

    # A fresh login now reaches content.
    member2 = login(u["email"], u["password"])
    assert member2.get("/api/subjects").status_code == 200


def test_reject_blocks_content_access(admin, user_factory, login, content):
    u = user_factory(status="pending")
    assert admin.post(f"/api/admin/users/{u['id']}/reject").get_json()["status"] == "rejected"
    member = login(u["email"], u["password"])
    assert member.get("/api/subjects").status_code == 403


def test_cannot_change_admin_status(admin, user_factory):
    other_admin = user_factory(status="approved", is_admin=True)
    assert admin.post(f"/api/admin/users/{other_admin['id']}/reject").status_code == 400


def test_approve_missing_user_404(admin):
    assert admin.post("/api/admin/users/999999/approve").status_code == 404
