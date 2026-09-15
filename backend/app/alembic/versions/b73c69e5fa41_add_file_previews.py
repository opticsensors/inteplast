"""Persistent queue and cache metadata for disposable web previews.

Revision ID: b73c69e5fa41
Revises: a62f58d4e930
"""
from alembic import op
import sqlalchemy as sa

revision = "b73c69e5fa41"
down_revision = "a62f58d4e930"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "filepreview",
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("message", sa.String(255), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("triangles", sa.Integer(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["storedfile.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("file_id"),
    )
    op.create_index("ix_filepreview_state", "filepreview", ["state"])


def downgrade():
    op.drop_table("filepreview")
