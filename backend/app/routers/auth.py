from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, get_current_user
from app.repositories.auth_repo import AuthRepository
from app.schemas.api import LoginRequest, LoginResponse, RefreshRequest, TokenResponse, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    return await AuthService(session).login(body.username, body.password)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user = await AuthRepository(session).get_by_id(current_user.id)
    if not user or not user.is_active:
        raise PermissionError("Invalid token")
    return user


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    return await AuthService(session).refresh(body.refresh_token)


@router.post("/logout")
async def logout(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    await AuthService(session).logout(body.refresh_token)
    return {"status": "ok"}
