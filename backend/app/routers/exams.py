from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.schemas.api import ExamCreate, ExamOut
from app.services.exam_service import ExamService

router = APIRouter(prefix="/exams", tags=["exams"])


@router.post("", response_model=ExamOut, status_code=201)
async def create_exam(
    data: ExamCreate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    """Create a new exam.  Mains → P1 only.  Advanced → P1 + P2."""
    return await ExamService(session).create_exam(data)


@router.get("", response_model=list[ExamOut])
async def list_exams(
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await ExamService(session).list_exams()


@router.get("/{exam_id}/papers", response_model=list[str])
async def get_exam_papers(
    exam_id: int,
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    """Return authorized paper codes for an exam (e.g. ['P1'] or ['P1','P2'])."""
    return await ExamService(session).get_exam_papers(exam_id)
