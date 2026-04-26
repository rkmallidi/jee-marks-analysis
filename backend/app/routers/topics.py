from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.models.orm import Topic
from app.repositories.topic_repo import TopicRepository
from app.schemas.api import TopicCreate, TopicOut, TopicUpdate

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
async def list_topics(
    subject: str | None = Query(None),
    _: CurrentUser = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
):
    return await TopicRepository(session).list_topics(subject)


@router.post("", response_model=TopicOut, status_code=201)
async def create_topic(
    body: TopicCreate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    topic = Topic(subject=body.subject, name=body.name)
    return await TopicRepository(session).create(topic)


@router.patch("/{topic_id}", response_model=TopicOut)
async def update_topic(
    topic_id: int,
    body: TopicUpdate,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = TopicRepository(session)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise KeyError(f"Topic {topic_id} not found")
    return await repo.update(topic, body.model_dump(exclude_none=True))


@router.delete("/{topic_id}")
async def delete_topic(
    topic_id: int,
    _: CurrentUser = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
):
    repo = TopicRepository(session)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise KeyError(f"Topic {topic_id} not found")
    await repo.delete(topic)
    return {"status": "ok"}
