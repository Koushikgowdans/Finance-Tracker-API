from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import date

from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilters, PaginatedTransactions


def get_transaction_by_id(db: Session, transaction_id: int, user_id: int | None = None) -> Transaction:
    query = db.query(Transaction).filter(Transaction.id == transaction_id)
    if user_id is not None:
        query = query.filter(Transaction.user_id == user_id)
    tx = query.first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    return tx


def create_transaction(db: Session, data: TransactionCreate, user_id: int) -> Transaction:
    tx = Transaction(
        amount=data.amount,
        type=data.type,
        category=data.category.strip(),
        date=data.date,
        notes=data.notes,
        user_id=user_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def update_transaction(
    db: Session, transaction_id: int, data: TransactionUpdate, user_id: int | None = None
) -> Transaction:
    tx = get_transaction_by_id(db, transaction_id, user_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, transaction_id: int, user_id: int | None = None) -> None:
    tx = get_transaction_by_id(db, transaction_id, user_id)
    db.delete(tx)
    db.commit()


def list_transactions(
    db: Session,
    filters: TransactionFilters,
    user_id: int | None = None,
) -> PaginatedTransactions:
    query = db.query(Transaction)

    if user_id is not None:
        query = query.filter(Transaction.user_id == user_id)
    if filters.type:
        query = query.filter(Transaction.type == filters.type)
    if filters.category:
        query = query.filter(Transaction.category.ilike(f"%{filters.category}%"))
    if filters.date_from:
        query = query.filter(Transaction.date >= filters.date_from)
    if filters.date_to:
        query = query.filter(Transaction.date <= filters.date_to)

    total = query.count()
    offset = (filters.page - 1) * filters.page_size
    items = query.order_by(Transaction.date.desc()).offset(offset).limit(filters.page_size).all()

    return PaginatedTransactions(
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        items=items,
    )
