"""add partial_count to student_exam_summary and student_subject_summary

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_exam_summary",    sa.Column("partial_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("student_subject_summary", sa.Column("partial_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("student_subject_summary", "partial_count")
    op.drop_column("student_exam_summary",    "partial_count")
