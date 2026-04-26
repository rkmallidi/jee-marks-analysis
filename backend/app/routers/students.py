from __future__ import annotations

import io
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.schemas.api import StudentCreate, StudentOut, StudentUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/filters/options")
async def get_filter_options(
    _: CurrentUser       = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    """Get distinct values for filter dropdowns"""
    return await StudentService(session).get_filter_options()


@router.get("")
async def list_students(
    branch_name:   str | None = Query(None),
    program_name:  str | None = Query(None),
    section:       str | None = Query(None),
    student_class: str | None = Query(None),
    dean:          str | None = Query(None),
    status:        str | None = Query(None),
    search:        str | None = Query(None),
    page:          int        = Query(1, ge=1),
    page_size:     int        = Query(50, ge=1, le=200),
    current_user: CurrentUser    = Depends(require_role(["admin", "dean", "faculty"])),
    session:      AsyncSession   = Depends(get_session),
):
    svc     = StudentService(session)
    allowed = None
    if current_user.role == "faculty":
        allowed = await svc.get_allowed_sections_for_faculty(current_user.id)
    students, total = await svc.list_students(
        branch_name, program_name, section, status, allowed, search, page, page_size,
        student_class=student_class, dean=dean,
    )
    return {"total": total, "page": page, "page_size": page_size,
            "items": [StudentOut.model_validate(s) for s in students]}


@router.get("/export")
async def export_students(
    branch_name:  str | None = Query(None),
    program_name: str | None = Query(None),
    section:      str | None = Query(None),
    status:       str | None = Query(None),
    search:       str | None = Query(None),
    format:       Literal["csv", "xlsx"] = Query("csv"),
    current_user: CurrentUser    = Depends(require_role(["admin", "dean", "faculty"])),
    session:      AsyncSession   = Depends(get_session),
):
    svc     = StudentService(session)
    allowed = None
    if current_user.role == "faculty":
        allowed = await svc.get_allowed_sections_for_faculty(current_user.id)
    data, filename, mime = await svc.export_students(
        branch_name, program_name, section, status, allowed, search, format
    )
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{admission_no}", response_model=StudentOut)
async def get_student(
    admission_no: str,
    _: CurrentUser       = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await StudentService(session).get_student(admission_no)


@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    body: StudentCreate,
    _: CurrentUser       = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    return await StudentService(session).create_student(body)


@router.patch("/{admission_no}", response_model=StudentOut)
async def update_student(
    admission_no: str,
    body: StudentUpdate,
    _: CurrentUser       = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    return await StudentService(session).update_student(admission_no, body)


@router.delete("/{admission_no}", status_code=204)
async def delete_student(
    admission_no: str,
    _: CurrentUser       = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    await StudentService(session).delete_student(admission_no)
