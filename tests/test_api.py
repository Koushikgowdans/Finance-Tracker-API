"""
tests/test_api.py – Integration tests for the Finance Tracker API.

Run with:
    pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# ── In-memory SQLite for tests ──────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────────

def register(username="testuser", email="test@test.com", password="secret123", role="viewer"):
    return client.post("/auth/register", json={
        "username": username, "email": email, "password": password, "role": role,
    })


def login(username="testuser", password="secret123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def auth_headers(username="testuser", password="secret123"):
    resp = login(username, password)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_admin():
    register("admin", "admin@test.com", "admin123", "admin")
    return auth_headers("admin", "admin123")


def create_analyst():
    register("analyst", "analyst@test.com", "analyst123", "analyst")
    return auth_headers("analyst", "analyst123")


# ── Auth Tests ───────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_success(self):
        resp = register()
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["role"] == "viewer"
        assert "hashed_password" not in data

    def test_register_duplicate_username(self):
        register()
        resp = register()
        assert resp.status_code == 409

    def test_register_duplicate_email(self):
        register()
        resp = register(username="other")
        assert resp.status_code == 409

    def test_register_short_username(self):
        resp = register(username="ab")
        assert resp.status_code == 422

    def test_register_weak_password(self):
        resp = register(password="123")
        assert resp.status_code == 422

    def test_login_success(self):
        register()
        resp = login()
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self):
        register()
        resp = login(password="wrong")
        assert resp.status_code == 401

    def test_login_unknown_user(self):
        resp = login(username="nobody")
        assert resp.status_code == 401

    def test_me_authenticated(self):
        register()
        resp = client.get("/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_me_unauthenticated(self):
        resp = client.get("/auth/me")
        assert resp.status_code == 403


# ── Transaction Tests ─────────────────────────────────────────────────────────

VALID_TX = {
    "amount": 500.00,
    "type": "income",
    "category": "Salary",
    "date": "2024-03-15",
    "notes": "March salary",
}


class TestTransactions:
    def setup_method(self):
        register()
        self.headers = auth_headers()

    def _post_tx(self, payload=None, headers=None):
        return client.post("/transactions/", json=payload or VALID_TX, headers=headers or self.headers)

    def test_create_transaction(self):
        resp = self._post_tx()
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == 500.00
        assert data["type"] == "income"

    def test_create_transaction_negative_amount(self):
        payload = {**VALID_TX, "amount": -100}
        resp = self._post_tx(payload)
        assert resp.status_code == 422

    def test_create_transaction_zero_amount(self):
        payload = {**VALID_TX, "amount": 0}
        resp = self._post_tx(payload)
        assert resp.status_code == 422

    def test_create_transaction_empty_category(self):
        payload = {**VALID_TX, "category": "   "}
        resp = self._post_tx(payload)
        assert resp.status_code == 422

    def test_create_transaction_invalid_type(self):
        payload = {**VALID_TX, "type": "transfer"}
        resp = self._post_tx(payload)
        assert resp.status_code == 422

    def test_list_transactions(self):
        self._post_tx()
        self._post_tx()
        resp = client.get("/transactions/", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_transactions_filter_by_type(self):
        self._post_tx(VALID_TX)
        self._post_tx({**VALID_TX, "type": "expense", "category": "Rent"})
        resp = client.get("/transactions/?type=income", headers=self.headers)
        assert resp.json()["total"] == 1

    def test_list_transactions_filter_by_category(self):
        self._post_tx(VALID_TX)
        self._post_tx({**VALID_TX, "category": "Rent", "type": "expense"})
        resp = client.get("/transactions/?category=Salary", headers=self.headers)
        assert resp.json()["total"] == 1

    def test_list_transactions_pagination(self):
        for _ in range(5):
            self._post_tx()
        resp = client.get("/transactions/?page=1&page_size=2", headers=self.headers)
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_get_transaction_by_id(self):
        created = self._post_tx().json()
        resp = client.get(f"/transactions/{created['id']}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_transaction(self):
        resp = client.get("/transactions/9999", headers=self.headers)
        assert resp.status_code == 404

    def test_update_transaction(self):
        created = self._post_tx().json()
        resp = client.patch(
            f"/transactions/{created['id']}",
            json={"amount": 750.00, "notes": "Updated"},
            headers=self.headers,
        )
        assert resp.status_code == 200
        assert resp.json()["amount"] == 750.00

    def test_update_transaction_invalid_amount(self):
        created = self._post_tx().json()
        resp = client.patch(
            f"/transactions/{created['id']}",
            json={"amount": -50},
            headers=self.headers,
        )
        assert resp.status_code == 422

    def test_delete_transaction(self):
        created = self._post_tx().json()
        resp = client.delete(f"/transactions/{created['id']}", headers=self.headers)
        assert resp.status_code == 204
        resp = client.get(f"/transactions/{created['id']}", headers=self.headers)
        assert resp.status_code == 404

    def test_viewer_cannot_see_other_users_transactions(self):
        # Create a second user and their transaction
        register("other", "other@test.com")
        other_headers = auth_headers("other")
        tx = client.post("/transactions/", json=VALID_TX, headers=other_headers).json()

        # testuser (viewer) should not see other's transaction
        resp = client.get(f"/transactions/{tx['id']}", headers=self.headers)
        assert resp.status_code == 404

    def test_unauthenticated_cannot_list(self):
        resp = client.get("/transactions/")
        assert resp.status_code == 403


# ── Analytics Tests ───────────────────────────────────────────────────────────

class TestAnalytics:
    def setup_method(self):
        register()
        self.headers = auth_headers()
        # Add sample transactions
        client.post("/transactions/", json={**VALID_TX, "amount": 3000, "type": "income", "category": "Salary"}, headers=self.headers)
        client.post("/transactions/", json={**VALID_TX, "amount": 500, "type": "expense", "category": "Rent"}, headers=self.headers)
        client.post("/transactions/", json={**VALID_TX, "amount": 200, "type": "expense", "category": "Groceries"}, headers=self.headers)

    def test_summary_totals(self):
        resp = client.get("/analytics/summary", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_income"] == 3000.0
        assert data["total_expenses"] == 700.0
        assert data["balance"] == 2300.0
        assert data["transaction_count"] == 3

    def test_summary_category_breakdown(self):
        resp = client.get("/analytics/summary", headers=self.headers)
        data = resp.json()
        expense_cats = {c["category"]: c["total"] for c in data["expense_by_category"]}
        assert expense_cats["Rent"] == 500.0
        assert expense_cats["Groceries"] == 200.0

    def test_my_summary(self):
        resp = client.get("/analytics/my-summary", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["transaction_count"] == 3

    def test_summary_date_filter(self):
        resp = client.get("/analytics/summary?date_from=2025-01-01&date_to=2025-01-31", headers=self.headers)
        assert resp.status_code == 200
        # All seeded transactions use 2024-03-15, so this range should return zeroes
        assert resp.json()["transaction_count"] == 0

    def test_analyst_sees_all_users(self):
        analyst_headers = create_analyst()
        client.post("/transactions/", json=VALID_TX, headers=analyst_headers)
        resp = client.get("/analytics/summary", headers=analyst_headers)
        # Analyst summary covers all users
        assert resp.json()["transaction_count"] >= 1


# ── Role-Based Access Tests ───────────────────────────────────────────────────

class TestRoleAccess:
    def test_admin_can_list_users(self):
        register()
        admin_headers = create_admin()
        resp = client.get("/users/", headers=admin_headers)
        assert resp.status_code == 200

    def test_viewer_cannot_list_users(self):
        register()
        resp = client.get("/users/", headers=auth_headers())
        assert resp.status_code == 403

    def test_admin_can_delete_any_transaction(self):
        register()
        viewer_headers = auth_headers()
        tx = client.post("/transactions/", json=VALID_TX, headers=viewer_headers).json()
        admin_headers = create_admin()
        resp = client.delete(f"/transactions/{tx['id']}", headers=admin_headers)
        assert resp.status_code == 204

    def test_viewer_cannot_delete_others_transaction(self):
        register("user1", "u1@test.com")
        register("user2", "u2@test.com")
        h1 = auth_headers("user1")
        h2 = auth_headers("user2")
        tx = client.post("/transactions/", json=VALID_TX, headers=h1).json()
        resp = client.delete(f"/transactions/{tx['id']}", headers=h2)
        assert resp.status_code == 404
