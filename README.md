# 💰 Finance Tracker API

A clean, well-structured **FastAPI** backend for personal finance management with role-based access control, analytics, and full CRUD support for financial transactions.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Seeding Demo Data](#seeding-demo-data)
- [Running Tests](#running-tests)
- [API Reference](#api-reference)
- [Role-Based Access Control](#role-based-access-control)
- [Assumptions & Design Decisions](#assumptions--design-decisions)

---

## Overview

Finance Tracker is a Python-powered REST API that allows users to:

- **Record and manage** income and expense transactions
- **Filter transactions** by type, category, and date range
- **View financial summaries** including totals, category breakdowns, monthly trends, and recent activity
- **Operate with role-based access** (Viewer, Analyst, Admin) that controls what each user can see and do

---

## Project Structure

```
finance-tracker/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # SQLAlchemy setup, session factory, init_db()
│   ├── models/
│   │   ├── user.py          # User ORM model + UserRole enum
│   │   └── transaction.py   # Transaction ORM model + TransactionType enum
│   ├── schemas/
│   │   ├── user.py          # Pydantic schemas for user I/O + validation
│   │   ├── transaction.py   # Pydantic schemas for transactions + filters
│   │   └── analytics.py     # Pydantic schemas for summary responses
│   ├── services/
│   │   ├── auth_service.py        # Password hashing, JWT creation/decoding
│   │   ├── user_service.py        # User CRUD business logic
│   │   ├── transaction_service.py # Transaction CRUD + filter logic
│   │   └── analytics_service.py   # Summary and aggregation logic
│   ├── middleware/
│   │   └── auth.py          # JWT dependency, get_current_user, require_role()
│   └── routers/
│       ├── auth.py          # /auth — register, login, me
│       ├── users.py         # /users — admin user management
│       ├── transactions.py  # /transactions — CRUD + filtering
│       └── analytics.py     # /analytics — summaries
├── tests/
│   └── test_api.py          # Integration test suite (pytest)
├── seed.py                  # Demo data seeder
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Component       | Choice                          |
|-----------------|---------------------------------|
| Framework       | FastAPI                         |
| Database        | SQLite (via SQLAlchemy ORM)     |
| Validation      | Pydantic v2                     |
| Authentication  | JWT (PyJWT) + bcrypt (passlib)  |
| Testing         | pytest + HTTPX (TestClient)     |

SQLite was chosen for simplicity and zero-config setup. The SQLAlchemy ORM layer makes swapping to PostgreSQL or MySQL a one-line change in `database.py`.

---

## Setup & Installation

**Prerequisites:** Python 3.11+

```bash
# 1. Clone / download the project
cd finance-tracker

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at **http://127.0.0.1:8000**

Interactive API docs (Swagger UI): **http://127.0.0.1:8000/docs**  
ReDoc: **http://127.0.0.1:8000/redoc**

---

## Seeding Demo Data

Populate the database with 4 demo users and 160 realistic transactions:

```bash
python seed.py
```

Demo credentials created:

| Role     | Username  | Password    |
|----------|-----------|-------------|
| admin    | admin     | admin123    |
| analyst  | analyst   | analyst123  |
| viewer   | alice     | alice123    |
| viewer   | bob       | bob123      |

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use an **in-memory SQLite database** — no setup required, and they don't affect your development database.

The test suite covers:

- Auth: register, login, token validation, field validation
- Transactions: CRUD, filtering, pagination, ownership enforcement
- Analytics: totals, category breakdown, date filtering
- RBAC: role restrictions on all protected endpoints

---

## API Reference

### Authentication

| Method | Endpoint         | Description                    | Auth Required |
|--------|------------------|--------------------------------|---------------|
| POST   | `/auth/register` | Create a new user account      | No            |
| POST   | `/auth/login`    | Login and receive a JWT token  | No            |
| GET    | `/auth/me`       | Get current user's profile     | Yes           |

**Login response:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { "id": 1, "username": "alice", "role": "viewer", ... }
}
```

Use the token in all subsequent requests:
```
Authorization: Bearer <access_token>
```

---

### Transactions

| Method | Endpoint                   | Description                          | Min Role |
|--------|----------------------------|--------------------------------------|----------|
| GET    | `/transactions/`           | List transactions (paginated)        | viewer   |
| POST   | `/transactions/`           | Create a new transaction             | viewer   |
| GET    | `/transactions/{id}`       | Get a transaction by ID              | viewer   |
| PATCH  | `/transactions/{id}`       | Update a transaction                 | viewer   |
| DELETE | `/transactions/{id}`       | Delete a transaction                 | viewer   |

**Create / Update payload:**
```json
{
  "amount": 1500.00,
  "type": "income",
  "category": "Salary",
  "date": "2024-06-01",
  "notes": "June paycheck"
}
```

**Filtering query params:**
```
GET /transactions/?type=expense&category=Rent&date_from=2024-01-01&date_to=2024-06-30&page=1&page_size=20
```

**Paginated response:**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [ ... ]
}
```

---

### Analytics

| Method | Endpoint               | Description                                    | Min Role |
|--------|------------------------|------------------------------------------------|----------|
| GET    | `/analytics/summary`   | Full financial summary (scoped by role)        | viewer   |
| GET    | `/analytics/my-summary`| Personal summary for the current user          | viewer   |

**Summary response:**
```json
{
  "total_income": 12000.00,
  "total_expenses": 4500.00,
  "balance": 7500.00,
  "transaction_count": 38,
  "income_by_category": [
    { "category": "Salary", "total": 9000.00, "count": 3 }
  ],
  "expense_by_category": [
    { "category": "Rent", "total": 2400.00, "count": 3 }
  ],
  "monthly_totals": [
    { "year": 2024, "month": 4, "income": 3000.00, "expenses": 1200.00, "net": 1800.00 }
  ],
  "recent_transactions": [ ... ]
}
```

Optional date filters: `?date_from=2024-01-01&date_to=2024-12-31`

---

### Users (Admin only)

| Method | Endpoint        | Description           | Min Role |
|--------|-----------------|-----------------------|----------|
| GET    | `/users/`       | List all users        | admin    |
| GET    | `/users/{id}`   | Get user by ID        | self/admin |
| PATCH  | `/users/{id}`   | Update role or email  | admin    |
| DELETE | `/users/{id}`   | Delete a user         | admin    |

---

## Role-Based Access Control

| Capability                              | Viewer | Analyst | Admin |
|-----------------------------------------|--------|---------|-------|
| Create transactions (own)               | ✓      | ✓       | ✓     |
| View own transactions                   | ✓      | ✓       | ✓     |
| View all transactions                   | ✗      | ✗       | ✓     |
| Edit own transactions                   | ✓      | ✓       | ✓     |
| Edit any transaction                    | ✗      | ✗       | ✓     |
| Delete own transactions                 | ✓      | ✓       | ✓     |
| Delete any transaction                  | ✗      | ✗       | ✓     |
| View own financial summary              | ✓      | ✓       | ✓     |
| View global financial summary           | ✗      | ✓       | ✓     |
| Manage users (list, update, delete)     | ✗      | ✗       | ✓     |

---

## Assumptions & Design Decisions

1. **SQLite as default DB** — zero-config for evaluation; swap to PostgreSQL by changing `DATABASE_URL` in `database.py`.

2. **Viewers own their data** — Viewer and Analyst roles can only read/write their own transactions. Admins have full access across all users.

3. **Analysts see aggregate analytics** — The `/analytics/summary` endpoint returns global data for analysts/admins, and personal data for viewers. `/analytics/my-summary` always returns the caller's own data regardless of role.

4. **Amounts are always positive** — The `type` field (`income` / `expense`) captures direction; the `amount` field is always a positive number. Validation enforces `amount > 0`.

5. **JWT-based auth** — Tokens expire after 24 hours. The secret key is hardcoded for this assessment; in production it would be loaded from an environment variable.

6. **Soft role assignment at registration** — The registration endpoint accepts a `role` field. In a production system, role assignment would be an admin-only operation; here it's open for easy testing.

7. **Category is a free-text string** — No predefined category list, keeping the schema flexible. Category search uses case-insensitive `ILIKE` matching.

8. **`updated_at` tracking** — Transactions record both `created_at` and `updated_at` timestamps for audit purposes.
