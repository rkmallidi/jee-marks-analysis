from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session
from app.dependencies import CurrentUser, require_role
from app.models.orm import (
    AggregateSummary, Alert, ExamPaper, GradedResult, OmrResponse,
    Question, RankAudit, RankSummary, Result,
    StudentExamSummary, StudentSubjectSummary, StudentTopicSummary,
)
from app.schemas.api import QuestionCreate, QuestionOut, QuestionUpdate

router = APIRouter(prefix="/questions", tags=["questions"])


async def _load_question(session: AsyncSession, question_id: int) -> Question:
    r = await session.execute(
        select(Question)
        .options(selectinload(Question.exam_paper))
        .where(Question.id == question_id)
    )
    q = r.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.get("")
async def list_questions(
    exam_id:    int = Query(...),
    paper_code: str = Query(...),
    _:       CurrentUser  = Depends(require_role(["admin", "dean", "faculty"])),
    session: AsyncSession = Depends(get_session),
) -> list[QuestionOut]:
    r = await session.execute(
        select(Question)
        .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
        .options(selectinload(Question.exam_paper))
        .where(ExamPaper.exam_id == exam_id, ExamPaper.paper_code == paper_code)
        .order_by(Question.question_no)
    )
    return [QuestionOut.model_validate(q) for q in r.scalars().all()]


@router.delete("/paper", status_code=200)
async def clean_paper(
    exam_id:    int = Query(...),
    paper_code: str = Query(...),
    _:       CurrentUser  = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete all questions for a paper plus all derived/calculated data for the exam."""
    ep = (await session.execute(
        select(ExamPaper).where(
            ExamPaper.exam_id == exam_id,
            ExamPaper.paper_code == paper_code,
        )
    )).scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Paper not found")

    q_ids = list((await session.execute(
        select(Question.id).where(Question.exam_paper_id == ep.id)
    )).scalars().all())

    if not q_ids:
        return {"deleted_questions": 0, "message": "Paper already empty"}

    # Clear dependent rows (responses + graded reference question_id)
    await session.execute(delete(OmrResponse).where(OmrResponse.question_id.in_(q_ids)))
    await session.execute(delete(GradedResult).where(GradedResult.question_id.in_(q_ids)))

    # Clear all exam-level computed tables
    for model in (
        StudentExamSummary, StudentSubjectSummary, StudentTopicSummary,
        RankSummary, AggregateSummary, Alert, RankAudit, Result,
    ):
        await session.execute(delete(model).where(model.exam_id == exam_id))  # type: ignore[attr-defined]

    # Finally remove the questions themselves
    await session.execute(delete(Question).where(Question.exam_paper_id == ep.id))
    await session.flush()

    return {"deleted_questions": len(q_ids), "message": f"Cleaned {len(q_ids)} questions and all derived data"}


@router.post("", status_code=201)
async def create_question(
    body:    QuestionCreate,
    _:       CurrentUser  = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
) -> QuestionOut:
    ep = (await session.execute(
        select(ExamPaper).where(
            ExamPaper.exam_id == body.exam_id,
            ExamPaper.paper_code == body.paper_code,
        )
    )).scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="ExamPaper not found for given exam_id/paper_code")

    clash = (await session.execute(
        select(func.count()).where(
            Question.exam_paper_id == ep.id,
            Question.question_no == body.question_no,
        )
    )).scalar_one()
    if clash:
        raise HTTPException(
            status_code=409,
            detail=f"Question {body.question_no} already exists in paper {body.paper_code}",
        )

    q = Question(
        exam_paper_id=ep.id,
        question_no=body.question_no,
        subject=body.subject,
        topic=body.topic,
        sub_topic=body.sub_topic,
        question_type=body.question_type,
        positive_marks=body.positive_marks,
        negative_marks=body.negative_marks,
        partial_marks=body.partial_marks,
        correct_option_bkc=body.correct_option_bkc,
        is_deleted_bkc=body.is_deleted_bkc,
        correct_option_akc=body.correct_option_akc,
        is_deleted_akc=body.is_deleted_akc,
    )
    session.add(q)
    await session.flush()
    q = await _load_question(session, q.id)
    return QuestionOut.model_validate(q)


@router.patch("/{question_id}")
async def update_question(
    question_id: int,
    body:    QuestionUpdate,
    _:       CurrentUser  = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
) -> QuestionOut:
    q = await _load_question(session, question_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(q, field, value)
    await session.flush()
    await session.refresh(q)
    # reload relationship after refresh
    await session.execute(
        select(Question)
        .options(selectinload(Question.exam_paper))
        .where(Question.id == question_id)
    )
    q = await _load_question(session, question_id)
    return QuestionOut.model_validate(q)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: int,
    _:       CurrentUser  = Depends(require_role(["admin"])),
    session: AsyncSession = Depends(get_session),
) -> None:
    q = await _load_question(session, question_id)

    resp_count = (await session.execute(
        select(func.count()).where(OmrResponse.question_id == question_id)
    )).scalar_one()

    if resp_count:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {resp_count} student response(s) exist for this question. "
                   "Clear responses first or mark it as deleted instead.",
        )

    await session.delete(q)
    await session.flush()
