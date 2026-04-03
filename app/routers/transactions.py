from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database import get_db
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionRead,
    TransactionFilters, PaginatedTransactions,
)
from app.models.transaction import TransactionType
from app.models.user import User, UserRole
from app.services.transaction_service import (
    create_transaction, update_transaction, delete_transaction,
    list_transactions, get_transaction_by_id,
)
from app.middleware.auth import get_current_user, require_admin, require_viewer_or_above

router = APIRouter()


def _viewer_user_id(current_user: User) -> Optional[int]:
    """Viewers and analysts see only their own records; admins see all."""
    if current_user.role == UserRole.admin:
        return None
    return current_user.id


@router.get("/", response_model=PaginatedTransactions)
def get_transactions(
    type: Optional[TransactionType] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_above),
):
    """
    List transactions with optional filters.
    - **Viewers / Analysts**: see only their own transactions.
    - **Admins**: see all transactions.
    """
    filters = TransactionFilters(
        type=type, category=category, date_from=date_from,
        date_to=date_to, page=page, page_size=page_size,
    )
    return list_transactions(db, filters, user_id=_viewer_user_id(current_user))


@router.post("/", response_model=TransactionRead, status_code=201)
def add_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new transaction for the current user."""
    return create_transaction(db, data, user_id=current_user.id)


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_above),
):
    """Retrieve a single transaction by ID."""
    return get_transaction_by_id(db, transaction_id, user_id=_viewer_user_id(current_user))


@router.patch("/{transaction_id}", response_model=TransactionRead)
def edit_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a transaction.
    - Regular users can only edit their own transactions.
    - Admins can edit any transaction.
    """
    user_id = None if current_user.role == UserRole.admin else current_user.id
    return update_transaction(db, transaction_id, data, user_id=user_id)


@router.delete("/{transaction_id}", status_code=204)
def remove_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a transaction.
    - Regular users can only delete their own transactions.
    - Admins can delete any transaction.
    """
    user_id = None if current_user.role == UserRole.admin else current_user.id
    delete_transaction(db, transaction_id, user_id=user_id)
