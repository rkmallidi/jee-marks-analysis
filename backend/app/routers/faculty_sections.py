from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.models.orm import FacultySection
from app.repositories.branch_repo import BranchRepository
from app.repositories.faculty_section_repo import FacultySectionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.api import FacultySectionCreate, FacultySectionOut

router = APIRouter(prefix="/faculty-sections", tags=["faculty-sections"])


def _to_out(fs: FacultySection) -> FacultySectionOut:
    return FacultySectionOut(
        id=fs.id,
        user_id=fs.user_id,
        branch_id=fs.branch_id,
        section=fs.section,
        username=fs.user.username,
        full_name=fs.user.full_name,
        branch_name=fs.branch.name,
    )


@router.get("", response_model=list[FacultySectionOut])
async def list_faculty_sections(
    _: CurrentUser = Depends(require_role(["admin", "dean"])),
    session: AsyncSession = Depends(get_session),
):
    sections = await FacultySectionRepository(session).list_all()
    return [_to_out(fs) for fs in sections]


@router.post("", response_model=FacultySectionOut, status_code=201)
async def create_faculty_section(
    body: FacultySectionCreate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    user = await UserRepository(session).get_by_id(body.user_id)
    if not user:
        raise KeyError(f"User {body.user_id} not found")
    branch = await BranchRepository(session).get_by_id(body.branch_id)
    if not branch:
        raise KeyError(f"Branch {body.branch_id} not found")

    repo = FacultySectionRepository(session)
    fs = FacultySection(user_id=body.user_id, branch_id=body.branch_id, section=body.section)
    created = await repo.create(fs)
    refreshed = await repo.get_by_id(created.id)
    return _to_out(refreshed)


@router.delete("/{fs_id}")
async def delete_faculty_section(
    fs_id: int,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = FacultySectionRepository(session)
    fs = await repo.get_by_id(fs_id)
    if not fs:
        raise KeyError(f"FacultySection {fs_id} not found")
    await repo.delete(fs)
    return {"status": "ok"}
