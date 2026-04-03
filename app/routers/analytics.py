from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database import get_db
from app.schemas.analytics import FinancialSummary, AnalyticsFilters
from app.models.user import User, UserRole
from app.services.analytics_service import get_financial_summary
from app.middleware.auth import require_viewer_or_above, require_analyst_or_above

router = APIRouter()


def _scoped_user_id(current_user: User) -> Optional[int]:
    """Admins and analysts can request cross-user summaries; viewers see only their own."""
    if current_user.role in (UserRole.admin, UserRole.analyst):
        return None
    return current_user.id


@router.get("/summary", response_model=FinancialSummary)
def summary(
    date_from: Optional[date] = Query(None, description="Start date (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_above),
):
    """
    Return a full financial summary including totals, category breakdowns,
    monthly trends, and recent transactions.

    - **Viewers**: summary is scoped to their own transactions only.
    - **Analysts / Admins**: summary covers all transactions.
    """
    user_id = _scoped_user_id(current_user)
    return get_financial_summary(db, user_id=user_id, date_from=date_from, date_to=date_to)


@router.get("/my-summary", response_model=FinancialSummary)
def my_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_above),
):
    """
    Return the authenticated user's own financial summary, regardless of role.
    """
    return get_financial_summary(db, user_id=current_user.id, date_from=date_from, date_to=date_to)
