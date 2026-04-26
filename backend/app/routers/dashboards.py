from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.exam_repo import ExamRepository
from app.schemas.api import ExamOut
from app.services.dashboard_service import DashboardService
from app.services.student_service import StudentService

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/overall/{exam_id}")
async def overall(
    exam_id:      int,
    _:            CurrentUser  = Depends(require_role(["admin", "dean", "faculty"])),
    session:      AsyncSession = Depends(get_session),
):
    result = await DashboardService(session).get_overall(exam_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    return result


@router.get("/exam-trend/{exam_id}")
async def exam_trend(
    exam_id: int,
    _:       CurrentUser  = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await DashboardService(session).get_exam_trend(exam_id)


@router.get("/weak-students/{exam_id}")
async def weak_students(
    exam_id:  int,
    severity: str | None  = Query(None),
    rule_key: str | None  = Query(None),
    current_user: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession     = Depends(get_session),
):
    allowed_nos = None
    if current_user.role == "faculty":
        svc      = StudentService(session)
        sections = await svc.get_allowed_sections_for_faculty(current_user.id)
        students, _ = await svc.list_students(None, None, None, "active", sections)
        allowed_nos = [s.admission_no for s in students]
    return await DashboardService(session).get_weak_students(exam_id, severity, rule_key, allowed_nos)


@router.get("/subject-analysis/{exam_id}")
async def subject_analysis(
    exam_id:     int,
    scope:       str = Query("overall"),
    scope_value: str = Query("all"),
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await DashboardService(session).get_subjects(exam_id, scope, scope_value)


@router.get("/topic-heatmap/{exam_id}")
async def topic_heatmap(
    exam_id: int,
    section: str | None   = Query(None),
    current_user: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession     = Depends(get_session),
):
    svc         = StudentService(session)
    student_ids = None

    if current_user.role == "faculty":
        sections = await svc.get_allowed_sections_for_faculty(current_user.id)
        if section and section not in sections:
            raise HTTPException(status_code=403, detail="Not assigned to that section")
        students, _ = await svc.list_students(None, None, section, "active", sections)
        student_ids = [s.admission_no for s in students]
    elif section:
        students, _ = await svc.list_students(None, None, section, "active", None)
        student_ids = [s.admission_no for s in students]

    return await DashboardService(session).get_topic_heatmap(exam_id, section, student_ids)


@router.get("/student/{admission_no}/exam/{exam_id}/responses")
async def student_exam_responses(
    admission_no: str,
    exam_id:      int,
    _:            CurrentUser  = Depends(require_role(["admin", "dean", "faculty"])),
    session:      AsyncSession = Depends(get_session),
):
    return await AnalyticsRepository(session).get_student_exam_responses(admission_no, exam_id)


@router.get("/student/{admission_no}")
async def student_deep_dive(
    admission_no: str,
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await DashboardService(session).get_student_deep_dive(admission_no)


@router.get("/leaderboard/{exam_id}")
async def leaderboard(
    exam_id: int,
    limit:   int = Query(10, ge=1, le=100),
    offset:  int = Query(0, ge=0),
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await AnalyticsRepository(session).get_leaderboard(exam_id, limit, offset)


@router.get("/score-distribution")
async def score_distribution(
    exam_id: int = Query(...),
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await AnalyticsRepository(session).get_percentile_distribution(exam_id)


@router.get("/exams", response_model=list[ExamOut])
async def list_exams(
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await ExamRepository(session).list_exams()
