from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.models.orm import User
from app.repositories.user_repo import UserRepository
from app.schemas.api import UserAdminOut, UserCreate, UserUpdate
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserAdminOut])
async def list_users(
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    return await UserRepository(session).list_users()


@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(
    body: UserCreate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    if await repo.get_by_username(body.username):
        raise ValueError(f"Username '{body.username}' already exists")
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    return await repo.create(user)


@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise KeyError(f"User {user_id} not found")
    data = body.model_dump(exclude_none=True)
    if "password" in data:
        data["hashed_password"] = hash_password(data.pop("password"))
    return await repo.update(user, data)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    if user_id == current_user.id:
        raise ValueError("Cannot delete your own account")
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise KeyError(f"User {user_id} not found")
    await repo.delete(user)
    return {"status": "ok"}
