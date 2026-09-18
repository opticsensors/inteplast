"""Prevent registering the same source folder as multiple parts.

Revision ID: e06f92b8cd74
Revises: d95e81a7bc63
"""

from alembic import op

revision = "e06f92b8cd74"
down_revision = "d95e81a7bc63"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_part_folder_path", "part", ["folder_path"], unique=True)


def downgrade():
    op.drop_index("ix_part_folder_path", table_name="part")
