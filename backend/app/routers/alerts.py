from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.schemas.api import AlertConfigUpdate, AlertOut
from app.services.alert_service import AlertService
from app.services.student_service import StudentService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    admission_no: str | None  = Query(None),
    exam_id:      int | None  = Query(None),
    severity:     str | None  = Query(None),
    rule_key:     str | None  = Query(None),
    acknowledged: bool | None = Query(None),
    current_user: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession     = Depends(get_session),
):
    allowed_nos = None
    if current_user.role == "faculty":
        svc      = StudentService(session)
        sections = await svc.get_allowed_sections_for_faculty(current_user.id)
        students, _ = await svc.list_students(None, None, None, "active", sections)
        allowed_nos = [s.admission_no for s in students]
    return await AlertService(session).list_alerts(
        admission_no, exam_id, severity, rule_key, acknowledged, allowed_nos
    )


@router.patch("/{alert_id}/acknowledge")
async def acknowledge(
    alert_id: int,
    current_user: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession     = Depends(get_session),
):
    await AlertService(session).acknowledge(alert_id, current_user.id)
    return {"status": "ok"}


@router.get("/config")
async def get_config(
    _: CurrentUser = Depends(require_role(["admin", "dean"])),
    session: AsyncSession = Depends(get_session),
):
    configs = await AlertService(session).get_configs()
    return [{"rule_key": c.rule_key, "config": c.config_json} for c in configs]


@router.patch("/config")
async def update_config(
    rule_key: str             = Query(...),
    body: AlertConfigUpdate   = ...,
    current_user: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession     = Depends(get_session),
):
    await AlertService(session).update_config(rule_key, body.config, current_user.id)
    return {"status": "ok"}
