"""Test set-up: an in-memory SQLite database and fast password hashing.

Settings are read when the app is imported, so the environment is prepared first.
"""
import os
import secrets

os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", "sqlite://"),
        "SECRET_KEY": secrets.token_urlsafe(48),
        "PASSWORD_HASH_ITERATIONS": "2000",
        "GEMINI_API_KEY": "",
        "LOGIN_MAX_ATTEMPTS": "3",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.org_setup import sync_rbac  # noqa: E402

PASSWORD = "Strong#Pass1"


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        sync_rbac(db)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class Company:
    """Registers a company through the API and creates one user per role."""

    def __init__(self, client: TestClient, name: str, prefix: str):
        self.c = client
        domain = prefix.lower()
        r = client.post(
            "/api/auth/register-organization",
            json={"organization_name": name, "request_prefix": prefix, "name": "Ada Admin",
                  "email": f"admin@{domain}.test", "password": PASSWORD},
        )
        assert r.status_code == 201, r.text
        self.admin = r.json()["access_token"]
        self.admin_user = r.json()["user"]
        self.tokens = {"admin": self.admin}
        self.ids = {"admin": self.admin_user["id"]}
        for key, role in [("manager", "Manager"), ("tech", "Technician"), ("tech2", "Technician"),
                          ("emp", "Employee"), ("emp2", "Employee")]:
            r = client.post("/api/users", headers=auth(self.admin),
                            json={"name": f"{key.title()} Person", "email": f"{key}@{domain}.test",
                                  "password": PASSWORD, "role": role})
            assert r.status_code == 201, r.text
            self.ids[key] = r.json()["id"]
            self.tokens[key] = self.login(f"{key}@{domain}.test")
        self.category_id = self.get("emp", "/api/organization/categories").json()[0]["id"]
        self.location_id = self.get("emp", "/api/organization/locations").json()[0]["id"]

    def login(self, email: str, password: str = PASSWORD) -> str:
        r = self.c.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    def h(self, who: str) -> dict:
        return auth(self.tokens[who])

    def get(self, who: str, url: str, **kw):
        return self.c.get(url, headers=self.h(who), **kw)

    def post(self, who: str, url: str, body: dict | None = None):
        return self.c.post(url, headers=self.h(who), json=body or {})

    def new_request(self, who: str = "emp", **overrides) -> dict:
        body = {"title": "Leaking tap", "description": "Kitchen tap drips all day long.",
                "category_id": self.category_id, "location_id": self.location_id, "priority": "Medium"}
        body.update(overrides)
        r = self.post(who, "/api/requests", body)
        assert r.status_code == 201, r.text
        return r.json()


@pytest.fixture()
def acme(client):
    return Company(client, "Acme Test", "ACME")


@pytest.fixture()
def other(client):
    return Company(client, "Other Corp", "OTH")
