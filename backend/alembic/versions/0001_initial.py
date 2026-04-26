"""initial schema with PostgreSQL extensions

Revision ID: 0001
Revises:
Create Date: 2026-04-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

revision     = "0001"
down_revision = None
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Enable pg_trgm for future fuzzy search on names
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table("branches",
        sa.Column("id",         sa.Integer,      primary_key=True, autoincrement=True),
        sa.Column("name",       sa.String(100),  nullable=False,   unique=True),
        sa.Column("city",       sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("topics",
        sa.Column("id",      sa.Integer,     primary_key=True, autoincrement=True),
        sa.Column("subject", sa.String(20),  nullable=False),
        sa.Column("name",    sa.String(200), nullable=False),
        sa.UniqueConstraint("subject", "name"),
    )
    op.create_table("users",
        sa.Column("id",              sa.Integer,                  primary_key=True, autoincrement=True),
        sa.Column("username",        sa.String(50),               nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(200),              nullable=False),
        sa.Column("full_name",       sa.String(100),              nullable=False),
        sa.Column("role",            sa.String(20),               nullable=False),
        sa.Column("is_active",       sa.Boolean,                  nullable=False, server_default="true"),
        sa.Column("created_at",      sa.DateTime(timezone=True),  server_default=sa.func.now()),
    )
    op.create_table("refresh_tokens",
        sa.Column("id",          sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("user_id",     sa.Integer,                 sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("token_hash",  sa.String(200),             nullable=False, unique=True),
        sa.Column("expires_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at",  sa.DateTime(timezone=True)),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])

    op.create_table("students",
        sa.Column("id",            sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("admission_no",  sa.String(15),              nullable=False, unique=True),
        sa.Column("name",          sa.String(150),             nullable=False),
        sa.Column("branch_name",   sa.String(100),             nullable=False),
        sa.Column("program_name",  sa.String(50),              nullable=False),
        sa.Column("student_class", sa.String(30),              nullable=False),
        sa.Column("section",       sa.String(10),              nullable=False),
        sa.Column("dean",          sa.String(100),             nullable=False),
        sa.Column("status",        sa.String(20),              nullable=False, server_default="'active'"),
        sa.Column("search_vector", TSVECTOR),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_students_branch",  "students", ["branch_name"])
    op.create_index("idx_students_section", "students", ["section"])
    op.create_index("idx_students_status",  "students", ["status"])
    op.create_index("idx_students_program", "students", ["program_name"])
    op.create_index("idx_students_fts",     "students", ["search_vector"],
                    postgresql_using="gin")

    # PostgreSQL trigger: keep search_vector up-to-date on insert/update
    op.execute("""
        CREATE OR REPLACE FUNCTION students_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                to_tsvector('english', coalesce(NEW.name, '')) ||
                to_tsvector('simple',  coalesce(NEW.admission_no, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trig_students_fts
        BEFORE INSERT OR UPDATE ON students
        FOR EACH ROW EXECUTE FUNCTION students_search_vector_update()
    """)

    op.create_table("faculty_sections",
        sa.Column("id",        sa.Integer,  primary_key=True, autoincrement=True),
        sa.Column("user_id",   sa.Integer,  sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("branch_id", sa.Integer,  sa.ForeignKey("branches.id")),
        sa.Column("section",   sa.String(10), nullable=False),
        sa.UniqueConstraint("user_id", "branch_id", "section"),
    )
    op.create_table("exams",
        sa.Column("id",         sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("exam_code",  sa.String(50),              nullable=False, unique=True),
        sa.Column("title",      sa.String(200)),
        sa.Column("exam_date",  sa.Date),
        sa.Column("exam_type",  sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("papers",
        sa.Column("id",         sa.Integer,  primary_key=True, autoincrement=True),
        sa.Column("exam_id",    sa.Integer,  sa.ForeignKey("exams.id", ondelete="CASCADE")),
        sa.Column("paper_code", sa.String(10), nullable=False),
        sa.UniqueConstraint("exam_id", "paper_code"),
    )
    op.create_table("questions",
        sa.Column("id",                  sa.Integer,  primary_key=True, autoincrement=True),
        sa.Column("paper_id",            sa.Integer,  sa.ForeignKey("papers.id", ondelete="CASCADE")),
        sa.Column("question_no",         sa.Integer,  nullable=False),
        sa.Column("subject",             sa.String(20), nullable=False),
        sa.Column("topic_id",            sa.Integer,  sa.ForeignKey("topics.id")),
        sa.Column("sub_topic",           sa.String(200)),
        sa.Column("question_type",       sa.String(20), nullable=False),
        sa.Column("positive_marks",      sa.Float,    nullable=False, server_default="0"),
        sa.Column("negative_marks",      sa.Float,    nullable=False, server_default="0"),
        sa.Column("partial_marks",       sa.Float,    nullable=False, server_default="0"),
        sa.Column("correct_option",      sa.String(20)),
        sa.Column("numerical_answer",    sa.Float),
        sa.Column("numerical_range_min", sa.Float),
        sa.Column("numerical_range_max", sa.Float),
        sa.UniqueConstraint("paper_id", "question_no"),
    )
    op.create_index("idx_questions_paper",   "questions", ["paper_id"])
    op.create_index("idx_questions_subject", "questions", ["subject"])

    op.create_table("answer_keys",
        sa.Column("id",                  sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("question_id",         sa.Integer,                 sa.ForeignKey("questions.id", ondelete="CASCADE")),
        sa.Column("key_type",            sa.String(3),               nullable=False),
        sa.Column("correct_option",      sa.String(20)),
        sa.Column("numerical_answer",    sa.Float),
        sa.Column("numerical_range_min", sa.Float),
        sa.Column("numerical_range_max", sa.Float),
        sa.Column("marks_override",      sa.Float),
        sa.Column("is_deleted",          sa.Boolean,                 nullable=False, server_default="false"),
        sa.Column("uploaded_at",         sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("uploaded_by",         sa.Integer,                 sa.ForeignKey("users.id")),
        sa.UniqueConstraint("question_id", "key_type"),
    )
    op.create_table("omr_responses",
        sa.Column("id",           sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("student_id",   sa.Integer,                 sa.ForeignKey("students.id")),
        sa.Column("question_id",  sa.Integer,                 sa.ForeignKey("questions.id")),
        sa.Column("exam_id",      sa.Integer,                 sa.ForeignKey("exams.id")),
        sa.Column("response_raw", sa.String(50),              nullable=False, server_default="''"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "question_id"),
    )
    op.create_index("idx_omr_student_exam", "omr_responses", ["student_id", "exam_id"])
    op.create_index("idx_omr_exam",         "omr_responses", ["exam_id"])

    op.create_table("graded_results",
        sa.Column("id",           sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("student_id",   sa.Integer,                 sa.ForeignKey("students.id")),
        sa.Column("question_id",  sa.Integer,                 sa.ForeignKey("questions.id")),
        sa.Column("exam_id",      sa.Integer,                 sa.ForeignKey("exams.id")),
        sa.Column("key_type",     sa.String(3),               nullable=False),
        sa.Column("marks_awarded", sa.Float,                  nullable=False),
        sa.Column("verdict",      sa.String(10),              nullable=False),
        sa.Column("is_attempted", sa.Boolean,                 nullable=False),
        sa.Column("graded_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "question_id", "key_type"),
    )
    op.create_index("idx_graded_exam",         "graded_results", ["exam_id"])
    op.create_index("idx_graded_student_exam", "graded_results", ["student_id", "exam_id"])

    # ── Analytics tables ─────────────────────────────────────────────────────
    op.create_table("student_exam_summary",
        sa.Column("id",               sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("student_id",       sa.Integer, sa.ForeignKey("students.id")),
        sa.Column("exam_id",          sa.Integer, sa.ForeignKey("exams.id")),
        sa.Column("total_marks",      sa.Float,   nullable=False),
        sa.Column("max_marks",        sa.Float,   nullable=False),
        sa.Column("percentage",       sa.Float,   nullable=False),
        sa.Column("attempted_count",  sa.Integer, nullable=False),
        sa.Column("correct_count",    sa.Integer, nullable=False),
        sa.Column("wrong_count",      sa.Integer, nullable=False),
        sa.Column("blank_count",      sa.Integer, nullable=False),
        sa.Column("negative_marks",   sa.Float,   nullable=False, server_default="0"),
        sa.Column("rank_overall",     sa.Integer),
        sa.Column("rank_branch",      sa.Integer),
        sa.Column("rank_program",     sa.Integer),
        sa.Column("rank_section",     sa.Integer),
        sa.Column("percentile_overall", sa.Float),
        sa.UniqueConstraint("student_id", "exam_id"),
    )
    op.create_index("idx_ses_exam_student", "student_exam_summary", ["exam_id", "student_id"])
    op.create_index("idx_ses_exam_rank",    "student_exam_summary", ["exam_id", "rank_overall"])

    op.create_table("student_subject_summary",
        sa.Column("id",          sa.Integer,  primary_key=True, autoincrement=True),
        sa.Column("student_id",  sa.Integer,  sa.ForeignKey("students.id")),
        sa.Column("exam_id",     sa.Integer,  sa.ForeignKey("exams.id")),
        sa.Column("subject",     sa.String(20), nullable=False),
        sa.Column("marks",       sa.Float,    nullable=False),
        sa.Column("max_marks",   sa.Float,    nullable=False),
        sa.Column("accuracy",    sa.Float,    nullable=False),
        sa.Column("attempted",   sa.Integer,  nullable=False),
        sa.Column("correct",     sa.Integer,  nullable=False),
        sa.Column("rank_subject", sa.Integer),
        sa.UniqueConstraint("student_id", "exam_id", "subject"),
    )
    op.create_index("idx_sss_exam_subject", "student_subject_summary", ["exam_id", "subject"])

    op.create_table("student_topic_summary",
        sa.Column("id",        sa.Integer,    primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer,   sa.ForeignKey("students.id")),
        sa.Column("exam_id",   sa.Integer,    sa.ForeignKey("exams.id")),
        sa.Column("subject",   sa.String(20), nullable=False),
        sa.Column("topic",     sa.String(200), nullable=False),
        sa.Column("marks",     sa.Float,      nullable=False),
        sa.Column("max_marks", sa.Float,      nullable=False),
        sa.Column("attempted", sa.Integer,    nullable=False),
        sa.Column("correct",   sa.Integer,    nullable=False),
        sa.Column("accuracy",  sa.Float,      nullable=False),
        sa.UniqueConstraint("student_id", "exam_id", "subject", "topic"),
    )
    op.create_index("idx_sts_student_topic", "student_topic_summary", ["student_id", "topic"])
    op.create_index("idx_sts_exam_topic",    "student_topic_summary", ["exam_id", "topic"])

    op.create_table("rank_summary",
        sa.Column("id",              sa.Integer,    primary_key=True, autoincrement=True),
        sa.Column("exam_id",         sa.Integer,    sa.ForeignKey("exams.id")),
        sa.Column("scope",           sa.String(20), nullable=False),
        sa.Column("scope_value",     sa.String(100), nullable=False),
        sa.Column("cutoff_top1pct",  sa.Float),
        sa.Column("cutoff_top5pct",  sa.Float),
        sa.Column("cutoff_top10pct", sa.Float),
        sa.Column("cutoff_top25pct", sa.Float),
        sa.Column("cutoff_median",   sa.Float),
        sa.UniqueConstraint("exam_id", "scope", "scope_value"),
    )
    op.create_table("aggregate_summary",
        sa.Column("id",          sa.Integer,    primary_key=True, autoincrement=True),
        sa.Column("exam_id",     sa.Integer,    sa.ForeignKey("exams.id")),
        sa.Column("scope",       sa.String(20), nullable=False),
        sa.Column("scope_value", sa.String(100), nullable=False),
        sa.Column("subject",     sa.String(20), nullable=False),
        sa.Column("avg",         sa.Float),
        sa.Column("median",      sa.Float),
        sa.Column("stdev",       sa.Float),
        sa.Column("min_score",   sa.Float),
        sa.Column("max_score",   sa.Float),
        sa.Column("n_students",  sa.Integer),
        sa.UniqueConstraint("exam_id", "scope", "scope_value", "subject"),
    )
    op.create_index("idx_agg_exam_scope", "aggregate_summary",
                    ["exam_id", "scope", "scope_value"])

    op.create_table("alert_config",
        sa.Column("id",          sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("rule_key",    sa.String(50),              nullable=False, unique=True),
        sa.Column("config_json", JSONB,                      nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by",  sa.Integer,                 sa.ForeignKey("users.id")),
    )
    op.create_table("alerts",
        sa.Column("id",              sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("student_id",      sa.Integer,                 sa.ForeignKey("students.id")),
        sa.Column("exam_id",         sa.Integer,                 sa.ForeignKey("exams.id")),
        sa.Column("rule_key",        sa.String(50),              nullable=False),
        sa.Column("severity",        sa.String(10),              nullable=False),
        sa.Column("title",           sa.String(200),             nullable=False),
        sa.Column("message",         sa.Text,                    nullable=False),
        sa.Column("context_json",    JSONB,                      nullable=False),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_by", sa.Integer,                 sa.ForeignKey("users.id")),
        sa.UniqueConstraint("student_id", "exam_id", "rule_key"),
    )
    op.create_index("idx_alerts_student",  "alerts", ["student_id"])
    op.create_index("idx_alerts_exam",     "alerts", ["exam_id"])
    op.create_index("idx_alerts_severity", "alerts", ["severity"])
    op.create_index("idx_alerts_context",  "alerts", ["context_json"],
                    postgresql_using="gin")

    op.create_table("rank_audit",
        sa.Column("id",           sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("student_id",   sa.Integer,                 sa.ForeignKey("students.id")),
        sa.Column("exam_id",      sa.Integer,                 sa.ForeignKey("exams.id")),
        sa.Column("key_type",     sa.String(3),               nullable=False),
        sa.Column("rank_before",  sa.Integer),
        sa.Column("rank_after",   sa.Integer),
        sa.Column("marks_before", sa.Float),
        sa.Column("marks_after",  sa.Float),
        sa.Column("logged_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rank_audit_exam", "rank_audit", ["exam_id"])

    op.create_table("upload_jobs",
        sa.Column("id",            sa.Integer,                 primary_key=True, autoincrement=True),
        sa.Column("upload_type",   sa.String(20),              nullable=False),
        sa.Column("filename",      sa.String(200),             nullable=False),
        sa.Column("status",        sa.String(20),              nullable=False, server_default="'pending'"),
        sa.Column("total_rows",    sa.Integer),
        sa.Column("accepted_rows", sa.Integer),
        sa.Column("rejected_rows", sa.Integer),
        sa.Column("error_json",    JSONB),
        sa.Column("uploaded_by",   sa.Integer,                 sa.ForeignKey("users.id")),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at",  sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_students_fts ON students")
    op.execute("DROP FUNCTION IF EXISTS students_search_vector_update()")
    for tbl in reversed([
        "upload_jobs", "rank_audit", "alerts", "alert_config",
        "aggregate_summary", "rank_summary", "student_topic_summary",
        "student_subject_summary", "student_exam_summary",
        "graded_results", "omr_responses", "answer_keys", "questions",
        "papers", "exams", "faculty_sections", "students",
        "refresh_tokens", "users", "topics", "branches",
    ]):
        op.drop_table(tbl)
