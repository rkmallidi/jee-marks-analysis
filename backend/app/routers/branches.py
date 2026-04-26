from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.models.orm import Branch
from app.repositories.branch_repo import BranchRepository
from app.schemas.api import BranchCreate, BranchOut, BranchUpdate

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("", response_model=list[BranchOut])
async def list_branches(
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await BranchRepository(session).list_branches()


@router.post("", response_model=BranchOut, status_code=201)
async def create_branch(
    body: BranchCreate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    branch = Branch(name=body.name, city=body.city)
    return await BranchRepository(session).create(branch)


@router.patch("/{branch_id}", response_model=BranchOut)
async def update_branch(
    branch_id: int,
    body: BranchUpdate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = BranchRepository(session)
    branch = await repo.get_by_id(branch_id)
    if not branch:
        raise KeyError(f"Branch {branch_id} not found")
    return await repo.update(branch, body.model_dump(exclude_none=True))


@router.delete("/{branch_id}")
async def delete_branch(
    branch_id: int,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = BranchRepository(session)
    branch = await repo.get_by_id(branch_id)
    if not branch:
        raise KeyError(f"Branch {branch_id} not found")
    await repo.delete(branch)
    return {"status": "ok"}
