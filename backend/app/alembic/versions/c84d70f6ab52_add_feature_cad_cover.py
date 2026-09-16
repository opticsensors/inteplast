"""Persist CAD cover selections and camera without changing source files.

Revision ID: c84d70f6ab52
Revises: b73c69e5fa41
"""
from alembic import op
import sqlalchemy as sa

revision = "c84d70f6ab52"
down_revision = "b73c69e5fa41"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("feature", sa.Column("cover_3d", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("feature", "cover_3d")
