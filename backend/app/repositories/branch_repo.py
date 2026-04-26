from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Branch


class BranchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_branches(self) -> list[Branch]:
        r = await self._s.execute(select(Branch).order_by(Branch.name))
        return list(r.scalars().all())

    async def get_by_id(self, branch_id: int) -> Branch | None:
        r = await self._s.execute(select(Branch).where(Branch.id == branch_id))
        return r.scalar_one_or_none()

    async def create(self, branch: Branch) -> Branch:
        self._s.add(branch)
        await self._s.flush()
        return branch

    async def update(self, branch: Branch, data: dict) -> Branch:
        for k, v in data.items():
            setattr(branch, k, v)
        await self._s.flush()
        return branch

    async def delete(self, branch: Branch) -> None:
        await self._s.delete(branch)
        await self._s.flush()
