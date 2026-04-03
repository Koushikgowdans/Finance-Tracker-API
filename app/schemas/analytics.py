from pydantic import BaseModel
from typing import Optional
from datetime import date


class CategoryBreakdown(BaseModel):
    category: str
    total: float
    count: int


class MonthlyTotal(BaseModel):
    year: int
    month: int
    income: float
    expenses: float
    net: float


class FinancialSummary(BaseModel):
    total_income: float
    total_expenses: float
    balance: float
    transaction_count: int
    income_by_category: list[CategoryBreakdown]
    expense_by_category: list[CategoryBreakdown]
    monthly_totals: list[MonthlyTotal]
    recent_transactions: list  # list[TransactionRead] – avoid circular import


class AnalyticsFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
