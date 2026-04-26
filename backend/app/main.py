from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.models.orm import Base
from app.routers import (
    alerts, auth, branches, dashboards, evaluation, exams,
    faculty_sections, questions, students, uploads, users,
)


async def _seed_papers_master() -> None:
    """Ensure P1 and P2 rows exist in papers_master (idempotent)."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(text("""
                INSERT INTO papers_master (paper_code)
                VALUES ('P1'), ('P2')
                ON CONFLICT (paper_code) DO NOTHING
            """))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "development":
        # create_all handles NEW tables; run the Alembic migration for
        # column changes on existing tables (topic_id → topic etc.)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Seed the fixed master table regardless of how schema was applied
        await _seed_papers_master()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="JEE Analytics Platform",
        version="1.0.0",
        description="Student performance intelligence for JEE coaching institutes",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Standard error envelope for every exception type ─────────────────────

    @app.exception_handler(KeyError)
    async def not_found(request: Request, exc: KeyError):
        # KeyError.__str__ wraps the message in quotes; use args[0] for clean output
        msg = exc.args[0] if exc.args else "Resource not found"
        return JSONResponse(status_code=404, content={
            "status": "failed", "error_code": "NOT_FOUND",
            "message": msg, "errors": [],
        })

    @app.exception_handler(PermissionError)
    async def forbidden(request: Request, exc: PermissionError):
        return JSONResponse(status_code=403, content={
            "status": "failed", "error_code": "FORBIDDEN",
            "message": str(exc), "errors": [],
        })

    @app.exception_handler(ValueError)
    async def validation_err(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={
            "status": "failed", "error_code": "VALIDATION_FAILED",
            "message": str(exc), "errors": [],
        })

    @app.exception_handler(Exception)
    async def generic_err(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={
            "status": "failed", "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.", "errors": [],
        })

    app.include_router(auth.router)
    app.include_router(students.router)
    app.include_router(exams.router)
    app.include_router(questions.router)
    app.include_router(uploads.router)
    app.include_router(evaluation.router)
    app.include_router(dashboards.router)
    app.include_router(alerts.router)
    app.include_router(users.router)
    app.include_router(branches.router)
    app.include_router(faculty_sections.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
