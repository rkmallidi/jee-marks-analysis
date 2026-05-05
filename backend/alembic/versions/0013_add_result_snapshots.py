"""add snapshot columns, rank_air, and is_absent to result summary tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # student_exam_summary — snapshot columns + AIR rank + absent flag
    op.add_column("student_exam_summary", sa.Column("rank_air",          sa.Integer(),     nullable=True))
    op.add_column("student_exam_summary", sa.Column("snap_program_name", sa.String(50),    nullable=True))
    op.add_column("student_exam_summary", sa.Column("snap_class_name",   sa.String(30),    nullable=True))
    op.add_column("student_exam_summary", sa.Column("snap_branch_name",  sa.String(100),   nullable=True))
    op.add_column("student_exam_summary", sa.Column("snap_section",      sa.String(10),    nullable=True))
    op.add_column("student_exam_summary", sa.Column("is_absent",         sa.Boolean(),     nullable=False, server_default="false"))
    op.create_index("idx_ses_exam_air", "student_exam_summary", ["exam_id", "rank_air"])

    # student_subject_summary — snapshot columns
    op.add_column("student_subject_summary", sa.Column("snap_branch_name", sa.String(100), nullable=True))
    op.add_column("student_subject_summary", sa.Column("snap_section",     sa.String(10),  nullable=True))

    # student_topic_summary — snapshot columns
    op.add_column("student_topic_summary", sa.Column("snap_branch_name", sa.String(100),   nullable=True))
    op.add_column("student_topic_summary", sa.Column("snap_section",     sa.String(10),    nullable=True))


def downgrade() -> None:
    op.drop_column("student_topic_summary",   "snap_section")
    op.drop_column("student_topic_summary",   "snap_branch_name")
    op.drop_column("student_subject_summary", "snap_section")
    op.drop_column("student_subject_summary", "snap_branch_name")
    op.drop_index("idx_ses_exam_air", table_name="student_exam_summary")
    op.drop_column("student_exam_summary", "is_absent")
    op.drop_column("student_exam_summary", "snap_section")
    op.drop_column("student_exam_summary", "snap_branch_name")
    op.drop_column("student_exam_summary", "snap_class_name")
    op.drop_column("student_exam_summary", "snap_program_name")
    op.drop_column("student_exam_summary", "rank_air")
