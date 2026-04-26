from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engines.alert_engine import AlertRecord
from app.models.orm import Alert, AlertConfig


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_alerts(self, records: list[AlertRecord]) -> None:
        """
        PostgreSQL ON CONFLICT DO UPDATE on (admission_no, exam_id, rule_key).
        Re-running the engine updates message + context without duplicating rows.
        """
        if not records:
            return

        # Deduplicate by constraint key — last record per (admission_no, exam_id, rule_key) wins.
        seen: dict[tuple, dict] = {}
        for r in records:
            seen[(r.admission_no, r.exam_id, r.rule_key)] = {
                "admission_no": r.admission_no,
                "exam_id":      r.exam_id,
                "rule_key":     r.rule_key,
                "severity":     r.severity,
                "title":        r.title,
                "message":      r.message,
                "context_json": r.context_json,
            }
        rows = list(seen.values())

        stmt = pg_insert(Alert).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["admission_no", "exam_id", "rule_key"],
            set_={
                "severity":     stmt.excluded.severity,
                "title":        stmt.excluded.title,
                "message":      stmt.excluded.message,
                "context_json": stmt.excluded.context_json,
                # preserve acknowledged_at / acknowledged_by — do NOT overwrite
            },
        )
        await self._s.execute(stmt)

    async def list_alerts(
        self,
        admission_no:          str | None   = None,
        exam_id:               int | None   = None,
        severity:              str | None   = None,
        rule_key:              str | None   = None,
        acknowledged:          bool | None  = None,
        allowed_admission_nos: list[str] | None = None,
    ) -> list[Alert]:
        q = select(Alert).options(selectinload(Alert.student), selectinload(Alert.exam))
        if admission_no:
            q = q.where(Alert.admission_no == admission_no)
        if exam_id:
            q = q.where(Alert.exam_id == exam_id)
        if severity:
            q = q.where(Alert.severity == severity)
        if rule_key:
            q = q.where(Alert.rule_key == rule_key)
        if acknowledged is True:
            q = q.where(Alert.acknowledged_at.isnot(None))
        elif acknowledged is False:
            q = q.where(Alert.acknowledged_at.is_(None))
        if allowed_admission_nos is not None:
            q = q.where(Alert.admission_no.in_(allowed_admission_nos))
        q = q.order_by(Alert.created_at.desc())
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def get_by_id(self, alert_id: int) -> Alert | None:
        r = await self._s.execute(select(Alert).where(Alert.id == alert_id))
        return r.scalar_one_or_none()

    async def acknowledge(self, alert: Alert, user_id: int) -> None:
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user_id
        await self._s.flush()

    async def get_all_configs(self) -> list[AlertConfig]:
        r = await self._s.execute(select(AlertConfig))
        return list(r.scalars().all())

    async def get_config_dict(self) -> dict[str, dict]:
        configs = await self.get_all_configs()
        return {c.rule_key: c.config_json for c in configs}

    async def upsert_config(self, rule_key: str, config: dict, user_id: int) -> None:
        """PostgreSQL ON CONFLICT upsert for alert_config."""
        stmt = pg_insert(AlertConfig).values(
            rule_key=rule_key, config_json=config, updated_by=user_id
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["rule_key"],
            set_={
                "config_json": stmt.excluded.config_json,
                "updated_by":  stmt.excluded.updated_by,
                "updated_at":  datetime.utcnow(),
            },
        )
        await self._s.execute(stmt)
