"""add program_name and student_class scope fields to exams

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("program_name",  sa.String(50),  nullable=True))
    op.add_column("exams", sa.Column("student_class", sa.String(30),  nullable=True))


def downgrade() -> None:
    op.drop_column("exams", "student_class")
    op.drop_column("exams", "program_name")
