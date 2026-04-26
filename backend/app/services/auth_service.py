from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.auth_repo import AuthRepository
from app.utils.security import verify_password


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _make_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub":  str(user_id),
        "role": role,
        "exp":  datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuthRepository(session)

    async def login(self, username: str, password: str) -> dict:
        user = await self._repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise PermissionError("Invalid credentials")

        access_token = _make_access_token(user.id, user.role)
        raw_refresh  = secrets.token_urlsafe(64)
        expires_at   = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        await self._repo.store_refresh_token(user.id, _hash_token(raw_refresh), expires_at)

        return {
            "access_token":  access_token,
            "refresh_token": raw_refresh,
            "token_type":    "bearer",
            "user":          user,
        }

    async def refresh(self, raw_token: str) -> dict:
        record = await self._repo.get_refresh_token(_hash_token(raw_token))
        if not record:
            raise PermissionError("Invalid or expired refresh token")

        # single-use: revoke old token before issuing new
        await self._repo.revoke_refresh_token(_hash_token(raw_token))

        user = await self._repo.get_by_id(record.user_id)
        if not user or not user.is_active:
            raise PermissionError("User is inactive")

        access_token = _make_access_token(user.id, user.role)
        raw_new      = secrets.token_urlsafe(64)
        expires_at   = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        await self._repo.store_refresh_token(user.id, _hash_token(raw_new), expires_at)

        return {
            "access_token":  access_token,
            "refresh_token": raw_new,
            "token_type":    "bearer",
        }

    async def logout(self, raw_token: str) -> None:
        await self._repo.revoke_refresh_token(_hash_token(raw_token))

    @staticmethod
    def decode_access_token(token: str) -> dict:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        except JWTError as e:
            raise PermissionError(f"Invalid token: {e}") from e
