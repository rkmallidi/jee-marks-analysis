"""redesign students table to match actual upload data

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TSVECTOR

revision     = "0002"
down_revision = "0001"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Drop the old FTS trigger + function first (references full_name)
    op.execute("DROP TRIGGER IF EXISTS trig_students_fts ON students")
    op.execute("DROP FUNCTION IF EXISTS students_search_vector_update()")

    # Drop old columns no longer needed
    op.drop_index("idx_students_branch", table_name="students")
    op.drop_index("idx_students_program", table_name="students", if_exists=True)
    op.drop_index("idx_students_fts", table_name="students")

    with op.batch_alter_table("students") as batch:
        batch.drop_column("full_name")
        batch.drop_column("gender")
        batch.drop_column("date_of_birth")
        batch.drop_constraint("students_branch_id_fkey", type_="foreignkey")
        batch.drop_column("branch_id")
        batch.drop_column("program")
        batch.drop_column("class")
        batch.drop_column("batch_year")
        batch.drop_column("guardian_phone")
        batch.drop_column("email")

        # Add new columns
        batch.add_column(sa.Column("name",          sa.String(150), nullable=False, server_default=""))
        batch.add_column(sa.Column("branch_name",   sa.String(100), nullable=False, server_default=""))
        batch.add_column(sa.Column("program_name",  sa.String(50),  nullable=False, server_default=""))
        batch.add_column(sa.Column("student_class", sa.String(30),  nullable=False, server_default=""))
        batch.add_column(sa.Column("dean",          sa.String(100), nullable=False, server_default=""))

        # Widen admission_no to 15 chars
        batch.alter_column("admission_no", type_=sa.String(15), existing_type=sa.String(12))

    # Remove server_defaults now that column is populated
    with op.batch_alter_table("students") as batch:
        batch.alter_column("name",          server_default=None)
        batch.alter_column("branch_name",   server_default=None)
        batch.alter_column("program_name",  server_default=None)
        batch.alter_column("student_class", server_default=None)
        batch.alter_column("dean",          server_default=None)

    # Recreate indexes on new columns
    op.create_index("idx_students_branch",  "students", ["branch_name"])
    op.create_index("idx_students_program", "students", ["program_name"])
    op.create_index("idx_students_fts",     "students", ["search_vector"], postgresql_using="gin")

    # Recreate FTS trigger using new `name` column
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

    # Drop programs table — no longer used
    op.drop_table("programs")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_students_fts ON students")
    op.execute("DROP FUNCTION IF EXISTS students_search_vector_update()")

    op.drop_index("idx_students_branch",  table_name="students")
    op.drop_index("idx_students_program", table_name="students")
    op.drop_index("idx_students_fts",     table_name="students")

    with op.batch_alter_table("students") as batch:
        batch.drop_column("name")
        batch.drop_column("branch_name")
        batch.drop_column("program_name")
        batch.drop_column("student_class")
        batch.drop_column("dean")
        batch.alter_column("admission_no", type_=sa.String(12), existing_type=sa.String(15))

        batch.add_column(sa.Column("full_name",      sa.String(100), nullable=False, server_default=""))
        batch.add_column(sa.Column("gender",         sa.String(1),   nullable=False, server_default="M"))
        batch.add_column(sa.Column("date_of_birth",  sa.Date,        nullable=False, server_default="2000-01-01"))
        batch.add_column(sa.Column("branch_id",      sa.Integer,     nullable=False, server_default="1"))
        batch.add_column(sa.Column("program",        sa.String(30),  nullable=False, server_default=""))
        batch.add_column(sa.Column("class",          sa.String(20),  nullable=False, server_default=""))
        batch.add_column(sa.Column("batch_year",     sa.Integer,     nullable=False, server_default="2024"))
        batch.add_column(sa.Column("guardian_phone", sa.String(10),  nullable=False, server_default="0000000000"))
        batch.add_column(sa.Column("email",          sa.String(200)))

    op.create_index("idx_students_branch", "students", ["branch_id"])
    op.create_index("idx_students_fts",    "students", ["search_vector"], postgresql_using="gin")
