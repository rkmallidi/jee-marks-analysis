from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import RefreshToken, User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_username(self, username: str) -> User | None:
        r = await self._s.execute(
            select(User).where(User.username == username, User.is_active.is_(True))
        )
        return r.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        r = await self._s.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()

    async def store_refresh_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> None:
        self._s.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))
        await self._s.flush()

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        r = await self._s.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.utcnow(),
            )
        )
        return r.scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str) -> None:
        token = await self.get_refresh_token(token_hash)
        if token:
            token.revoked_at = datetime.utcnow()
            await self._s.flush()

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        r = await self._s.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token in r.scalars().all():
            token.revoked_at = datetime.utcnow()
        await self._s.flush()
