from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.models.orm import UploadJob
from app.schemas.api import UploadJobOut
from app.services.upload_service import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/students")
async def upload_students(
    file: UploadFile,
    current_user: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession     = Depends(get_session),
):
    data = await file.read()
    return await UploadService(session, current_user.id).upload_students(
        data, file.filename or "students.xlsx"
    )


@router.post("/questions")
async def upload_questions(
    file:         UploadFile,
    exam_id:      int = Form(..., description="ID of the target exam"),
    paper_code:   str = Form(..., description="Paper code: P1 or P2"),
    current_user: CurrentUser  = Depends(require_role(["admin"])),
    session:      AsyncSession = Depends(get_session),
):
    """Upload questions (with BKC answers) for a specific exam paper."""
    data = await file.read()
    return await UploadService(session, current_user.id).upload_questions(
        data, file.filename or "questions.xlsx", exam_id, paper_code
    )


@router.post("/answer-key")
async def upload_answer_key(
    file:         UploadFile,
    exam_id:      int = Form(..., description="ID of the target exam"),
    paper_code:   str = Form(..., description="Paper code: P1 or P2"),
    key_type:     str = Form(..., description="BKC or AKC"),
    current_user: CurrentUser  = Depends(require_role(["admin"])),
    session:      AsyncSession = Depends(get_session),
):
    """Upload BKC or AKC answer corrections.

    CSV columns: qno (required), correct_answer (optional), is_deleted (optional).
    BKC → overwrites the base key answers on questions.
    AKC → sets amendment answers; AKC evaluation falls back to BKC for uncorrected questions.
    """
    if key_type not in ("BKC", "AKC"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="key_type must be BKC or AKC")
    data = await file.read()
    return await UploadService(session, current_user.id).upload_answer_key(
        data, file.filename or f"answer_key_{key_type.lower()}.csv",
        exam_id, paper_code, key_type
    )


@router.post("/responses")
async def upload_responses(
    file:         UploadFile,
    exam_id:      int = Form(..., description="ID of the target exam"),
    paper_code:   str = Form(..., description="Paper code: P1 or P2"),
    current_user: CurrentUser  = Depends(require_role(["admin"])),
    session:      AsyncSession = Depends(get_session),
):
    """Upload OMR responses — wide format: one row per student, question numbers as columns."""
    data = await file.read()
    return await UploadService(session, current_user.id).upload_responses(
        data, file.filename or "responses.csv", exam_id, paper_code
    )


@router.get("/jobs", response_model=list[UploadJobOut])
async def list_upload_jobs(
    exam_id: Optional[int]   = Query(None),
    _: CurrentUser           = Depends(require_role(["admin"])),
    session: AsyncSession    = Depends(get_session),
):
    stmt = select(UploadJob).order_by(UploadJob.created_at.desc()).limit(50)
    rows = (await session.execute(stmt)).scalars().all()
    return [UploadJobOut.model_validate(j) for j in rows]


@router.get("/errors")
async def get_errors(
    upload_id: int = Query(...),
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    job = await UploadService(session, 0).get_upload_job(upload_id)
    if not job:
        return {"upload_id": upload_id, "errors": []}
    return {"upload_id": upload_id, "errors": job.error_json or []}
