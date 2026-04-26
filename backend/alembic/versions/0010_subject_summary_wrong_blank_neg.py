"""add wrong, blank, negative_marks to student_subject_summary

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_subject_summary", sa.Column("wrong",          sa.Integer(), nullable=False, server_default="0"))
    op.add_column("student_subject_summary", sa.Column("blank",          sa.Integer(), nullable=False, server_default="0"))
    op.add_column("student_subject_summary", sa.Column("negative_marks", sa.Float(),   nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("student_subject_summary", "negative_marks")
    op.drop_column("student_subject_summary", "blank")
    op.drop_column("student_subject_summary", "wrong")
