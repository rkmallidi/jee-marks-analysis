from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
# PostgreSQL-specific column types used throughout
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Reference / lookup ────────────────────────────────────────────────────────

class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    faculty_sections: Mapped[list[FacultySection]] = relationship(back_populates="branch")


class PapersMaster(Base):
    """Fixed master table — only P1 and P2 are valid paper codes."""
    __tablename__ = "papers_master"

    paper_code: Mapped[str] = mapped_column(String(10), primary_key=True)

    exam_paper_links: Mapped[list[ExamPaper]] = relationship(back_populates="paper_master")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    __table_args__ = (UniqueConstraint("subject", "name"),)


# ── Users / Auth ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")
    faculty_sections: Mapped[list[FacultySection]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (Index("idx_refresh_tokens_user", "user_id"),)


# ── Students ──────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    admission_no: Mapped[str] = mapped_column(String(15), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(100), nullable=False)
    program_name: Mapped[str] = mapped_column(String(50), nullable=False)
    student_class: Mapped[str] = mapped_column(String(30), nullable=False)
    section: Mapped[str] = mapped_column(String(10), nullable=False)
    dean: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)

    responses: Mapped[list[OmrResponse]] = relationship(back_populates="student")
    exam_summaries: Mapped[list[StudentExamSummary]] = relationship(back_populates="student")
    alerts: Mapped[list[Alert]] = relationship(back_populates="student")

    __table_args__ = (
        Index("idx_students_branch", "branch_name"),
        Index("idx_students_section", "section"),
        Index("idx_students_status", "status"),
        Index("idx_students_program", "program_name"),
        Index("idx_students_fts", "search_vector", postgresql_using="gin"),
    )


class FacultySection(Base):
    __tablename__ = "faculty_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    section: Mapped[str] = mapped_column(String(10), nullable=False)

    user: Mapped[User] = relationship(back_populates="faculty_sections")
    branch: Mapped[Branch] = relationship(back_populates="faculty_sections")

    __table_args__ = (UniqueConstraint("user_id", "branch_id", "section"),)


# ── Exams / Papers / Questions ────────────────────────────────────────────────

class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    exam_date: Mapped[Optional[date]] = mapped_column(Date)
    # "Mains" → P1 only; "Advanced" → P1 + P2
    exam_type: Mapped[Optional[str]] = mapped_column(String(20))
    # Scope: which students this exam targets — drives AIR ranking and absent detection
    program_name:  Mapped[Optional[str]] = mapped_column(String(50))
    student_class: Mapped[Optional[str]] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    responses: Mapped[list[OmrResponse]] = relationship(back_populates="exam")
    exam_paper_links: Mapped[list[ExamPaper]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )


class ExamPaper(Base):
    """Authoritative mapping of which papers belong to an exam.
    Created automatically at exam creation time based on exam_type.
    Prevents P2 uploads for Mains exams.
    """
    __tablename__ = "exam_papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    paper_code: Mapped[str] = mapped_column(
        ForeignKey("papers_master.paper_code"), nullable=False
    )

    exam: Mapped[Exam] = relationship(back_populates="exam_paper_links")
    paper_master: Mapped[PapersMaster] = relationship(back_populates="exam_paper_links")
    questions: Mapped[list[Question]] = relationship(
        back_populates="exam_paper", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("exam_id", "paper_code"),)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_paper_id: Mapped[int] = mapped_column(ForeignKey("exam_papers.id", ondelete="CASCADE"))
    question_no: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    # Topic stored as plain string — no FK to topics table
    topic: Mapped[Optional[str]] = mapped_column(String(200))
    sub_topic: Mapped[Optional[str]] = mapped_column(String(200))
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    positive_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negative_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    partial_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # BKC answer — always set on question upload
    correct_option_bkc: Mapped[Optional[str]] = mapped_column(String(50))
    is_deleted_bkc:     Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    # AKC answer — NULL until an AKC correction is uploaded; NULL means "inherit BKC"
    correct_option_akc: Mapped[Optional[str]]  = mapped_column(String(50))
    is_deleted_akc:     Mapped[Optional[bool]] = mapped_column(Boolean)
    # Editorial difficulty — Easy | Medium | Hard | Very Hard; NULL = untagged
    difficulty:         Mapped[Optional[str]]  = mapped_column(String(20))

    exam_paper: Mapped[ExamPaper] = relationship(back_populates="questions")

    __table_args__ = (
        UniqueConstraint("exam_paper_id", "question_no"),
        Index("idx_questions_exam_paper", "exam_paper_id"),
        Index("idx_questions_subject", "subject"),
    )



# ── OMR Responses ─────────────────────────────────────────────────────────────

class OmrResponse(Base):
    __tablename__ = "omr_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    response_raw: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped[Student] = relationship(back_populates="responses")
    exam: Mapped[Exam] = relationship(back_populates="responses")
    question: Mapped[Question] = relationship()

    __table_args__ = (
        UniqueConstraint("admission_no", "question_id"),
        Index("idx_omr_student_exam", "admission_no", "exam_id"),
        Index("idx_omr_question", "question_id"),
        Index("idx_omr_exam", "exam_id"),
    )


class GradedResult(Base):
    __tablename__ = "graded_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    key_type: Mapped[str] = mapped_column(String(3), nullable=False)
    marks_awarded: Mapped[float] = mapped_column(Float, nullable=False)
    verdict: Mapped[str] = mapped_column(String(10), nullable=False)
    is_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("admission_no", "question_id", "key_type"),
        Index("idx_graded_exam", "exam_id"),
        Index("idx_graded_student_exam", "admission_no", "exam_id"),
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

class StudentExamSummary(Base):
    __tablename__ = "student_exam_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    total_marks: Mapped[float] = mapped_column(Float, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    attempted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    partial_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False)
    blank_count: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rank_overall: Mapped[Optional[int]] = mapped_column(Integer)
    rank_branch: Mapped[Optional[int]] = mapped_column(Integer)
    rank_program: Mapped[Optional[int]] = mapped_column(Integer)
    rank_section: Mapped[Optional[int]] = mapped_column(Integer)
    percentile_overall: Mapped[Optional[float]] = mapped_column(Float)
    # AIR = rank within same program_name + student_class (true All India Rank)
    rank_air: Mapped[Optional[int]] = mapped_column(Integer)
    # Snapshot of student attributes at exam time (preserved after transfers)
    snap_program_name: Mapped[Optional[str]] = mapped_column(String(50))
    snap_class_name:   Mapped[Optional[str]] = mapped_column(String(30))
    snap_branch_name:  Mapped[Optional[str]] = mapped_column(String(100))
    snap_section:      Mapped[Optional[str]] = mapped_column(String(10))
    is_absent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    student: Mapped[Student] = relationship(back_populates="exam_summaries")

    __table_args__ = (
        UniqueConstraint("admission_no", "exam_id"),
        Index("idx_ses_exam_student", "exam_id", "admission_no"),
        Index("idx_ses_exam_rank", "exam_id", "rank_overall"),
        Index("idx_ses_exam_air",  "exam_id", "rank_air"),
        Index("idx_ses_student", "admission_no"),
    )


class StudentSubjectSummary(Base):
    __tablename__ = "student_subject_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, nullable=False)
    partial_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    wrong: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    blank: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    negative_marks: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    rank_subject: Mapped[Optional[int]] = mapped_column(Integer)
    snap_branch_name: Mapped[Optional[str]] = mapped_column(String(100))
    snap_section:     Mapped[Optional[str]] = mapped_column(String(10))

    __table_args__ = (
        UniqueConstraint("admission_no", "exam_id", "subject"),
        Index("idx_sss_exam_subject", "exam_id", "subject"),
    )


class StudentTopicSummary(Base):
    __tablename__ = "student_topic_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    snap_branch_name: Mapped[Optional[str]] = mapped_column(String(100))
    snap_section:     Mapped[Optional[str]] = mapped_column(String(10))

    __table_args__ = (
        UniqueConstraint("admission_no", "exam_id", "subject", "topic"),
        Index("idx_sts_student_topic", "admission_no", "topic"),
        Index("idx_sts_exam_topic", "exam_id", "topic"),
    )


class RankSummary(Base):
    __tablename__ = "rank_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(100), nullable=False)
    cutoff_top1pct: Mapped[Optional[float]] = mapped_column(Float)
    cutoff_top5pct: Mapped[Optional[float]] = mapped_column(Float)
    cutoff_top10pct: Mapped[Optional[float]] = mapped_column(Float)
    cutoff_top25pct: Mapped[Optional[float]] = mapped_column(Float)
    cutoff_median: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("exam_id", "scope", "scope_value"),)


class AggregateSummary(Base):
    __tablename__ = "aggregate_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    avg: Mapped[Optional[float]] = mapped_column(Float)
    median: Mapped[Optional[float]] = mapped_column(Float)
    stdev: Mapped[Optional[float]] = mapped_column(Float)
    min_score: Mapped[Optional[float]] = mapped_column(Float)
    max_score: Mapped[Optional[float]] = mapped_column(Float)
    n_students: Mapped[Optional[int]] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("exam_id", "scope", "scope_value", "subject"),
        Index("idx_agg_exam_scope", "exam_id", "scope", "scope_value"),
    )


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertConfig(Base):
    __tablename__ = "alert_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    # JSONB: indexed, queryable, diff-able — far better than TEXT for config
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    rule_key: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # JSONB context lets the frontend query specific keys without full deserialization
    context_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    student: Mapped[Student] = relationship(back_populates="alerts")
    exam: Mapped["Exam"] = relationship()

    __table_args__ = (
        UniqueConstraint("admission_no", "exam_id", "rule_key"),
        Index("idx_alerts_student", "admission_no"),
        Index("idx_alerts_exam", "exam_id"),
        Index("idx_alerts_severity", "severity"),
        # GIN on JSONB context allows filtering alerts by specific context keys
        Index("idx_alerts_context", "context_json", postgresql_using="gin"),
    )


# ── Audit / Jobs ──────────────────────────────────────────────────────────────

class RankAudit(Base):
    __tablename__ = "rank_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(ForeignKey("students.admission_no"))
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    key_type: Mapped[str] = mapped_column(String(3), nullable=False)
    rank_before: Mapped[Optional[int]] = mapped_column(Integer)
    rank_after: Mapped[Optional[int]] = mapped_column(Integer)
    marks_before: Mapped[Optional[float]] = mapped_column(Float)
    marks_after: Mapped[Optional[float]] = mapped_column(Float)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_rank_audit_exam", "exam_id"),)


class UploadJob(Base):
    __tablename__ = "upload_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_rows: Mapped[Optional[int]] = mapped_column(Integer)
    accepted_rows: Mapped[Optional[int]] = mapped_column(Integer)
    rejected_rows: Mapped[Optional[int]] = mapped_column(Integer)
    # JSONB array of {row, column, message} error objects
    error_json: Mapped[Optional[list]] = mapped_column(JSONB)
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ── Paper-wise & Consolidated Results ─────────────────────────────────────────

class Result(Base):
    """Stores per-paper and consolidated scores after evaluation.

    result_type = "PAPER"        → one row per (student, exam, paper)
    result_type = "CONSOLIDATED" → one row per (student, exam); paper_code = NULL
                                   Advanced exams only (P1 + P2 combined)
    """
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.admission_no", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    paper_code: Mapped[Optional[str]] = mapped_column(String(10))  # NULL for CONSOLIDATED
    score: Mapped[float] = mapped_column(Float, nullable=False)
    total_marks: Mapped[float] = mapped_column(Float, nullable=False)
    result_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "PAPER" | "CONSOLIDATED"

    __table_args__ = (
        Index("idx_results_exam",         "exam_id"),
        Index("idx_results_student",      "student_id"),
        Index("idx_results_student_exam", "student_id", "exam_id"),
    )


# ── Rolling Averages ───────────────────────────────────────────────────────────

class RollingAverage(Base):
    """Cumulative average per student per exam type (Mains / Advanced), updated after each evaluation."""
    __tablename__ = "rolling_averages"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str]      = mapped_column(ForeignKey("students.admission_no"), nullable=False)
    exam_type:    Mapped[str]      = mapped_column(String(20), nullable=False)
    avg_score:    Mapped[float]    = mapped_column(Float, nullable=False)
    exam_count:   Mapped[int]      = mapped_column(Integer, nullable=False, server_default="0")
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("admission_no", "exam_type", name="uq_ra_student_type"),
        Index("idx_ra_student", "admission_no"),
    )


# ── Student Transfers ─────────────────────────────────────────────────────────

class StudentTransfer(Base):
    """Tracks when a student's program / branch / section changes."""
    __tablename__ = "student_transfers"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no:     Mapped[str]      = mapped_column(ForeignKey("students.admission_no"), nullable=False)
    changed_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    old_program_name: Mapped[str]      = mapped_column(String(50),  nullable=False)
    new_program_name: Mapped[str]      = mapped_column(String(50),  nullable=False)
    old_branch_name:  Mapped[str]      = mapped_column(String(100), nullable=False)
    new_branch_name:  Mapped[str]      = mapped_column(String(100), nullable=False)
    old_section:      Mapped[str]      = mapped_column(String(10),  nullable=False)
    new_section:      Mapped[str]      = mapped_column(String(10),  nullable=False)
    old_class:        Mapped[str]      = mapped_column(String(30),  nullable=False)
    new_class:        Mapped[str]      = mapped_column(String(30),  nullable=False)

    __table_args__ = (
        Index("idx_transfers_student",    "admission_no"),
        Index("idx_transfers_changed_at", "changed_at"),
    )
