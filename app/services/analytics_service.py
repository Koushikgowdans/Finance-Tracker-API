from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import Optional

from app.models.transaction import Transaction, TransactionType
from app.schemas.analytics import FinancialSummary, CategoryBreakdown, MonthlyTotal
from app.schemas.transaction import TransactionRead


def _base_query(db: Session, user_id: Optional[int], date_from: Optional[date], date_to: Optional[date]):
    query = db.query(Transaction)
    if user_id is not None:
        query = query.filter(Transaction.user_id == user_id)
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    return query


def get_financial_summary(
    db: Session,
    user_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> FinancialSummary:
    base = _base_query(db, user_id, date_from, date_to)

    # Totals
    income_result = (
        base.filter(Transaction.type == TransactionType.income)
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
        .scalar()
    )
    expense_result = (
        base.filter(Transaction.type == TransactionType.expense)
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
        .scalar()
    )
    total_income = round(float(income_result), 2)
    total_expenses = round(float(expense_result), 2)
    balance = round(total_income - total_expenses, 2)
    transaction_count = base.count()

    # Category breakdown — income
    income_cats = (
        _base_query(db, user_id, date_from, date_to)
        .filter(Transaction.type == TransactionType.income)
        .with_entities(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    income_by_category = [
        CategoryBreakdown(category=r.category, total=round(float(r.total), 2), count=r.count)
        for r in income_cats
    ]

    # Category breakdown — expenses
    expense_cats = (
        _base_query(db, user_id, date_from, date_to)
        .filter(Transaction.type == TransactionType.expense)
        .with_entities(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    expense_by_category = [
        CategoryBreakdown(category=r.category, total=round(float(r.total), 2), count=r.count)
        for r in expense_cats
    ]

    # Monthly totals
    monthly_raw = (
        _base_query(db, user_id, date_from, date_to)
        .with_entities(
            func.strftime("%Y", Transaction.date).label("year"),
            func.strftime("%m", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .group_by("year", "month", Transaction.type)
        .order_by("year", "month")
        .all()
    )

    monthly_map: dict[tuple, dict] = {}
    for row in monthly_raw:
        key = (int(row.year), int(row.month))
        if key not in monthly_map:
            monthly_map[key] = {"income": 0.0, "expenses": 0.0}
        if row.type == TransactionType.income:
            monthly_map[key]["income"] = round(float(row.total), 2)
        else:
            monthly_map[key]["expenses"] = round(float(row.total), 2)

    monthly_totals = [
        MonthlyTotal(
            year=k[0],
            month=k[1],
            income=v["income"],
            expenses=v["expenses"],
            net=round(v["income"] - v["expenses"], 2),
        )
        for k, v in sorted(monthly_map.items())
    ]

    # Recent activity (latest 10)
    recent = (
        _base_query(db, user_id, date_from, date_to)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(10)
        .all()
    )
    recent_transactions = [TransactionRead.model_validate(t) for t in recent]

    return FinancialSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        transaction_count=transaction_count,
        income_by_category=income_by_category,
        expense_by_category=expense_by_category,
        monthly_totals=monthly_totals,
        recent_transactions=recent_transactions,
    )
