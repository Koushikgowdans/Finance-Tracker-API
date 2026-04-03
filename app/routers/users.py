from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import get_all_users, get_user_by_id, update_user, delete_user
from app.middleware.auth import get_current_user, require_admin
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all users. Admin only."""
    return get_all_users(db)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a user by ID. Users can view their own profile; admins can view any."""
    if current_user.id != user_id and current_user.role.value != "admin":
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a user's email or role. Admin only."""
    return update_user(db, user_id, data, current_user)


@router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Delete a user. Admin only."""
    delete_user(db, user_id)
