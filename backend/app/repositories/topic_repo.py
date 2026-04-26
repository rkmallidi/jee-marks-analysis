from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Topic


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_topics(self, subject: str | None = None) -> list[Topic]:
        q = select(Topic).order_by(Topic.subject, Topic.name)
        if subject:
            q = q.where(Topic.subject == subject)
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def get_by_id(self, topic_id: int) -> Topic | None:
        r = await self._s.execute(select(Topic).where(Topic.id == topic_id))
        return r.scalar_one_or_none()

    async def create(self, topic: Topic) -> Topic:
        self._s.add(topic)
        await self._s.flush()
        return topic

    async def update(self, topic: Topic, data: dict) -> Topic:
        for k, v in data.items():
            setattr(topic, k, v)
        await self._s.flush()
        return topic

    async def delete(self, topic: Topic) -> None:
        await self._s.delete(topic)
        await self._s.flush()
