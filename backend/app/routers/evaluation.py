from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluate", tags=["evaluation"])


@router.post("/{exam_id}")
async def evaluate(
    exam_id:  int,
    key_type: str          = Query("BKC", description="BKC or AKC"),
    _:        CurrentUser  = Depends(require_role(["admin"])),
    session:  AsyncSession = Depends(get_session),
):
    """Grade all responses for an exam.

    key_type=BKC  → uses correct_option_bkc / is_deleted_bkc
    key_type=AKC  → uses correct_option_akc where set, falls back to BKC for uncorrected questions
    Both results are stored in graded_results under their respective key_type.
    """
    return await EvaluationService(session).evaluate(exam_id, key_type)


@router.post("/{exam_id}/dry-run")
async def dry_run(
    exam_id: int,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    return await EvaluationService(session).dry_run(exam_id)
