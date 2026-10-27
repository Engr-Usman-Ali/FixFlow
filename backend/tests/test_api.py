"""API tests. Names reference the SRS test scenarios (TC-xxx) and requirements."""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditEvent, User

from .conftest import PASSWORD, auth


# ------------------------------------------------------ SRS 10.3 scenarios ---
def test_tc001_submit_valid_request(acme):
    req = acme.new_request()
    assert req["ref"] == "ACME-00001"
    assert req["status"] == "New"
    assert req["creator"]["id"] == acme.ids["emp"]


def test_tc002_missing_field_is_identified(acme):
    r = acme.post("emp", "/api/requests", {"title": "No description", "category_id": acme.category_id,
                                           "location_id": acme.location_id})
    assert r.status_code == 422
    fields = [p["field"] for p in r.json()["detail"]]
    assert "description" in fields


def test_tc003_employee_cannot_assign(acme):
    req = acme.new_request()
    r = acme.post("emp", f"/api/requests/{req['id']}/assign", {"technician_id": acme.ids["tech"]})
    assert r.status_code == 403


def test_tc004_manager_assigns_with_history_and_notification(acme):
    req = acme.new_request()
    r = acme.post("manager", f"/api/requests/{req['id']}/assign", {"technician_id": acme.ids["tech"], "priority": "High"})
    assert r.status_code == 200, r.text
    detail = r.json()
    assert detail["status"] == "Assigned" and detail["priority"] == "High" and detail["priority_confirmed"]
    assert detail["assignments"][0]["technician"]["id"] == acme.ids["tech"]
    assert any(h["new_status"] == "Assigned" for h in detail["history"])
    notes = acme.get("tech", "/api/notifications").json()
    assert any(n["event_type"] == "assigned" and n["request_id"] == req["id"] for n in notes)


def test_tc005_resolve_requires_completion_details(acme):
    req = acme.new_request()
    acme.post("manager", f"/api/requests/{req['id']}/assign", {"technician_id": acme.ids["tech"]})
    assert acme.post("tech", f"/api/requests/{req['id']}/status", {"status": "In Progress"}).status_code == 200
    r = acme.post("tech", f"/api/requests/{req['id']}/status", {"status": "Resolved", "completion_details": "done"})
    assert r.status_code == 422 and "completion details" in r.json()["detail"]
    r = acme.post("tech", f"/api/requests/{req['id']}/status",
                  {"status": "Resolved", "completion_details": "Replaced the washer and tested for an hour."})
    assert r.status_code == 200 and r.json()["resolved_at"]


def test_tc006_work_log_records_actor_and_time(acme):
    req = acme.new_request()
    acme.post("manager", f"/api/requests/{req['id']}/assign", {"technician_id": acme.ids["tech"]})
    r = acme.post("tech", f"/api/requests/{req['id']}/work-logs",
                  {"diagnosis": "Worn washer", "action_taken": "Replaced it", "materials_used": "Washer 12mm"})
    assert r.status_code == 201
    assert r.json()["author"]["id"] == acme.ids["tech"] and r.json()["created_at"]


def test_tc007_unauthorized_request_is_not_disclosed(acme, other):
    req = acme.new_request("emp")
    assert acme.get("emp2", f"/api/requests/{req['id']}").status_code == 404  # another employee
    assert acme.get("tech", f"/api/requests/{req['id']}").status_code == 404  # not assigned
    assert other.get("manager", f"/api/requests/{req['id']}").status_code == 404  # other company
    found = acme.get("emp2", "/api/requests", params={"q": "Leaking"}).json()
    assert found["total"] == 0


def test_tc008_core_works_without_ai(acme):
    r = acme.post("emp", "/api/ai/suggest", {"title": "Broken light", "description": "The light in room 2 is out."})
    assert r.status_code == 503
    assert acme.get("emp", "/api/ai/status").json()["enabled"] is False
    acme.new_request()  # creating a request still works


def test_tc009_report_matches_known_data(acme):
    a = acme.new_request(priority="Critical")
    acme.new_request(priority="Low")
    acme.post("manager", f"/api/requests/{a['id']}/assign", {"technician_id": acme.ids["tech"]})
    s = acme.get("manager", "/api/reports/summary").json()
    assert s["total"] == 2
    assert s["by_priority"]["Critical"] == 1 and s["by_priority"]["Low"] == 1
    assert s["by_status"]["Assigned"] == 1 and s["by_status"]["New"] == 1
    tech_row = next(t for t in s["technician_workload"] if t["technician_id"] == acme.ids["tech"])
    assert tech_row["open"] == 1


def test_tc010_errors_are_safe(client, monkeypatch, acme):
    from app.routers import reports

    def boom(*_a, **_k):
        raise RuntimeError("database password=secret")

    monkeypatch.setattr(reports, "sla_for", boom)
    r = acme.get("manager", "/api/reports/summary")
    assert r.status_code == 500
    assert "secret" not in r.text and "Traceback" not in r.text


# ------------------------------------------------------------ RBAC rules ---
def test_reports_restricted_to_managers(acme):
    assert acme.get("emp", "/api/reports/summary").status_code == 403
    assert acme.get("tech", "/api/reports/summary").status_code == 403
    assert acme.get("admin", "/api/reports/summary").status_code == 403


def test_admin_manages_users_but_not_requests(acme):
    acme.new_request()
    assert acme.post("admin", "/api/requests", {"title": "x"}).status_code in (403, 422)
    assert acme.get("admin", "/api/requests").json()["total"] == 0  # least privilege
    assert acme.get("manager", "/api/users").status_code == 403
    assert acme.get("admin", "/api/users").status_code == 200
    assert acme.get("admin", "/api/audit").status_code == 200
    assert acme.get("manager", "/api/audit").status_code == 403


def test_technician_cannot_touch_another_technicians_job(acme):
    req = acme.new_request()
    acme.post("manager", f"/api/requests/{req['id']}/assign", {"technician_id": acme.ids["tech"]})
    assert acme.post("tech2", f"/api/requests/{req['id']}/status", {"status": "In Progress"}).status_code == 404
    assert acme.post("tech2", f"/api/requests/{req['id']}/work-logs", {"diagnosis": "x"}).status_code == 404


def test_hold_and_reject_need_reason(acme):
    req = acme.new_request()
    r = acme.post("manager", f"/api/requests/{req['id']}/status", {"status": "Rejected"})
    assert r.status_code == 422
    r = acme.post("manager", f"/api/requests/{req['id']}/status", {"status": "Rejected", "reason": "Duplicate of ACME-2"})
    assert r.status_code == 200 and r.json()["status"] == "Rejected"
    assert any(n["event_type"] == "status" for n in acme.get("emp", "/api/notifications").json())


def test_full_lifecycle_close_and_reopen(acme):
    req = acme.new_request()
    rid = req["id"]
    acme.post("manager", f"/api/requests/{rid}/status", {"status": "Under Review"})
    acme.post("manager", f"/api/requests/{rid}/assign", {"technician_id": acme.ids["tech"]})
    acme.post("tech", f"/api/requests/{rid}/status", {"status": "In Progress"})
    acme.post("tech", f"/api/requests/{rid}/status", {"status": "Resolved", "completion_details": "Fixed and tested fully."})
    assert acme.post("tech", f"/api/requests/{rid}/status", {"status": "Closed"}).status_code == 403
    r = acme.post("manager", f"/api/requests/{rid}/status", {"status": "Closed"})
    assert r.json()["closed_by"]["id"] == acme.ids["manager"] and r.json()["closed_at"]
    r = acme.post("manager", f"/api/requests/{rid}/status", {"status": "Under Review", "reason": "Leak is back"})
    assert r.status_code == 200 and r.json()["technician"] is None and r.json()["closed_at"] is None
    statuses = [h["new_status"] for h in r.json()["history"]]
    assert statuses == ["New", "Under Review", "Assigned", "In Progress", "Resolved", "Closed", "Under Review"]


def test_review_queue_filter(acme):
    a = acme.new_request()
    b = acme.new_request(title="Second issue")
    acme.post("manager", f"/api/requests/{b['id']}/assign", {"technician_id": acme.ids["tech"]})
    queue = acme.get("manager", "/api/requests", params=[("status", "New"), ("status", "Under Review")]).json()
    assert [i["id"] for i in queue["items"]] == [a["id"]]


# ------------------------------------------------------- company isolation ---
def test_companies_are_isolated(acme, other):
    acme.new_request()
    other_req = other.new_request()
    assert other_req["ref"] == "OTH-00001"  # each company numbers from 1
    assert other.get("manager", "/api/requests").json()["total"] == 1
    assert {u["email"].split("@")[1] for u in other.get("admin", "/api/users").json()} == {"oth.test"}
    # Cannot assign a technician from another company.
    r = other.post("manager", f"/api/requests/{other_req['id']}/assign", {"technician_id": acme.ids["tech"]})
    assert r.status_code == 422
    # Cannot edit users or use categories of another company.
    assert other.c.patch(f"/api/users/{acme.ids['emp']}", headers=other.h("admin"), json={"name": "Hacked"}).status_code == 404
    r = other.post("emp", "/api/requests", {"title": "Cross", "description": "Using another company's category",
                                            "category_id": acme.category_id, "location_id": other.location_id})
    assert r.status_code == 422


def test_equipment_codes_unique_per_company(acme, other):
    body = {"asset_code": "PMP-1", "name": "Pump", "category_id": acme.category_id, "location_id": acme.location_id}
    assert acme.post("manager", "/api/equipment", body).status_code == 201
    assert acme.post("manager", "/api/equipment", body).status_code == 409  # FR-054
    body.update(category_id=other.category_id, location_id=other.location_id)
    assert other.post("manager", "/api/equipment", body).status_code == 201  # same code, other company
    assert len(other.get("manager", "/api/equipment").json()) == 1


# ---------------------------------------------------------- authentication ---
def test_login_failure_does_not_reveal_account(client, acme):
    unknown = client.post("/api/auth/login", json={"email": "nobody@acme.test", "password": "Wrong#Pass1"})
    wrong = client.post("/api/auth/login", json={"email": "emp@acme.test", "password": "Wrong#Pass1"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_account_locks_after_repeated_failures(client, acme):
    for _ in range(3):
        client.post("/api/auth/login", json={"email": "emp2@acme.test", "password": "Wrong#Pass1"})
    r = client.post("/api/auth/login", json={"email": "emp2@acme.test", "password": PASSWORD})
    assert r.status_code == 401  # locked even with the right password
    assert acme.post("admin", f"/api/users/{acme.ids['emp2']}/unlock").status_code == 200
    assert client.post("/api/auth/login", json={"email": "emp2@acme.test", "password": PASSWORD}).status_code == 200


def test_logout_revokes_token(acme):
    token = acme.tokens["emp"]
    assert acme.c.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert acme.c.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_role_change_takes_effect_and_revokes_old_token(acme):
    old = acme.tokens["emp"]
    r = acme.c.patch(f"/api/users/{acme.ids['emp']}", headers=acme.h("admin"), json={"role": "Manager"})
    assert r.status_code == 200 and r.json()["role"] == "Manager"
    assert acme.c.get("/api/auth/me", headers=auth(old)).status_code == 401
    new = acme.login("emp@acme.test")
    assert "report.view" in acme.c.get("/api/auth/me", headers=auth(new)).json()["permissions"]


def test_last_admin_is_protected(acme):
    r = acme.c.patch(f"/api/users/{acme.ids['admin']}", headers=acme.h("admin"), json={"role": "Employee"})
    assert r.status_code == 409


def test_join_with_code_and_self_signup_switch(client, acme):
    code = acme.get("admin", "/api/organization").json()["join_code"]
    body = {"join_code": code.lower(), "name": "New Joiner", "email": "joiner@acme.test", "password": PASSWORD}
    r = client.post("/api/auth/join", json=body)
    assert r.status_code == 201 and r.json()["user"]["role"] == "Employee"
    acme.c.patch("/api/organization", headers=acme.h("admin"), json={"allow_self_signup": False})
    body["email"] = "late@acme.test"
    assert client.post("/api/auth/join", json=body).status_code == 403


def test_weak_password_rejected(client):
    r = client.post("/api/auth/register-organization", json={
        "organization_name": "Weak Co", "name": "W", "email": "w@weak.test", "password": "password"})
    assert r.status_code == 422


def test_change_password(acme):
    r = acme.post("emp", "/api/auth/change-password", {"current_password": PASSWORD, "new_password": "Another#Pass2"})
    assert r.status_code == 200
    acme.login("emp@acme.test", "Another#Pass2")


def test_passwords_are_salted_hashes(acme):
    with SessionLocal() as db:
        users = list(db.scalars(select(User)))
        assert all(PASSWORD not in u.password_hash for u in users)
        assert len({u.password_salt for u in users}) == len(users)  # unique salt each
        assert len({u.password_hash for u in users}) == len(users)  # same password, different hashes


def test_admin_actions_are_audited(acme):
    acme.c.patch(f"/api/users/{acme.ids['emp']}", headers=acme.h("admin"), json={"is_active": False})
    with SessionLocal() as db:
        actions = set(db.scalars(select(AuditEvent.action)))
    assert {"organization.created", "user.created", "user.updated"} <= actions
    page = acme.get("admin", "/api/audit", params={"action": "user."}).json()
    assert page["total"] >= 6


def test_gemini_suggestion_end_to_end(monkeypatch, acme):
    """Gemini is mocked: checks the key header, company categories in the schema, and validation."""
    import httpx

    from app.config import settings
    from app.services import gemini

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        text = '{"category": "Plumbing", "priority": "High", "rationale": "Water leak."}'
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(gemini.httpx, "post", fake_post)
    assert acme.get("emp", "/api/ai/status").json()["enabled"] is True
    r = acme.post("emp", "/api/ai/suggest", {"title": "Leaking pipe", "description": "Water under the sink in kitchen."})
    assert r.status_code == 200, r.text
    assert r.json()["category"] == "Plumbing" and r.json()["priority"] == "High"
    assert seen["headers"]["x-goog-api-key"] == "test-key"
    assert settings.gemini_model in seen["url"]
    enum = seen["body"]["generationConfig"]["responseSchema"]["properties"]["category"]["enum"]
    assert "Plumbing" in enum
    assert "acme.test" not in str(seen["body"])  # no personal data sent (FR-094)

    # Company switches AI off -> suggestions refused, workflow unaffected.
    acme.c.patch("/api/organization", headers=acme.h("admin"), json={"ai_enabled": False})
    assert acme.post("emp", "/api/ai/suggest", {"title": "Leaking pipe", "description": "Water under the sink."}).status_code == 503
