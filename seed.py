"""
seed.py – Populate the database with demo users and transactions.

Usage:
    python seed.py

This script is idempotent: running it multiple times will not create
duplicate users (it skips users that already exist).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
import random

from app.database import SessionLocal, init_db
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.schemas.transaction import TransactionCreate
from app.models.transaction import TransactionType
from app.services.user_service import create_user, get_user_by_username
from app.services.transaction_service import create_transaction
from sqlalchemy.exc import IntegrityError

USERS = [
    {"username": "admin", "email": "admin@finance.dev", "password": "admin123", "role": UserRole.admin},
    {"username": "analyst", "email": "analyst@finance.dev", "password": "analyst123", "role": UserRole.analyst},
    {"username": "alice", "email": "alice@finance.dev", "password": "alice123", "role": UserRole.viewer},
    {"username": "bob", "email": "bob@finance.dev", "password": "bob123", "role": UserRole.viewer},
]

INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Rental", "Bonus", "Gift"]
EXPENSE_CATEGORIES = ["Rent", "Groceries", "Utilities", "Transport", "Entertainment", "Health", "Education", "Dining"]

INCOME_NOTES = [
    "Monthly salary", "Freelance project payment", "Dividend payout",
    "Rental income", "Performance bonus", "Gift from family",
]
EXPENSE_NOTES = [
    "Monthly rent", "Weekly grocery run", "Electricity bill",
    "Metro pass", "Movie tickets", "Doctor visit", "Online course",
    "Restaurant dinner", "Coffee subscription", "Gym membership",
]


def random_date(days_back: int = 365) -> date:
    return date.today() - timedelta(days=random.randint(0, days_back))


def seed_transactions(db, user_id: int, count: int = 40):
    for _ in range(count):
        is_income = random.random() < 0.35  # ~35% income, ~65% expense
        if is_income:
            tx = TransactionCreate(
                amount=round(random.uniform(500, 8000), 2),
                type=TransactionType.income,
                category=random.choice(INCOME_CATEGORIES),
                date=random_date(),
                notes=random.choice(INCOME_NOTES),
            )
        else:
            tx = TransactionCreate(
                amount=round(random.uniform(10, 1200), 2),
                type=TransactionType.expense,
                category=random.choice(EXPENSE_CATEGORIES),
                date=random_date(),
                notes=random.choice(EXPENSE_NOTES),
            )
        create_transaction(db, tx, user_id=user_id)


def main():
    print("Initialising database …")
    init_db()

    db = SessionLocal()
    try:
        created_users = []
        for u in USERS:
            existing = get_user_by_username(db, u["username"])
            if existing:
                print(f"  ⚠  User '{u['username']}' already exists – skipping.")
                created_users.append(existing)
                continue
            user = create_user(db, UserCreate(**u))
            created_users.append(user)
            print(f"  ✓  Created user '{user.username}' (role: {user.role.value})")

        print("\nSeeding transactions …")
        for user in created_users:
            seed_transactions(db, user.id, count=40)
            print(f"  ✓  Added 40 transactions for '{user.username}'")

        print("\nSeed complete! Demo credentials:")
        for u in USERS:
            print(f"  {u['role'].value:10s}  username={u['username']}  password={u['password']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
