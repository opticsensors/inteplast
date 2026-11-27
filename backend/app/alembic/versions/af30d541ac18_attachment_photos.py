"""Ordered photos for each attachment gallery."""

import sqlalchemy as sa
from alembic import op

revision = "af30d541ac18"
down_revision = "f712a86bd504"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachmentphoto",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("part_id", sa.Uuid(), sa.ForeignKey("part.id", ondelete="CASCADE")),
        sa.Column(
            "file_id", sa.Uuid(), sa.ForeignKey("storedfile.id", ondelete="CASCADE")
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "image_id",
            sa.Uuid(),
            sa.ForeignKey("storedfile.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.CheckConstraint("(part_id IS NULL) <> (file_id IS NULL)"),
        sa.UniqueConstraint("part_id", "kind", "position"),
        sa.UniqueConstraint("file_id", "kind", "position"),
    )
    op.create_index("ix_attachmentphoto_image_id", "attachmentphoto", ["image_id"])
    op.execute("""
        WITH links AS (
            SELECT part_id, kind, file_id FROM partfile
            UNION SELECT part_id, kind, file_id FROM partreference
            UNION SELECT part_id, kind, file_id FROM partdocument
            UNION SELECT part_id, kind::text, file_id FROM featureasset
        ), photos AS (
            SELECT DISTINCT l.part_id,
                CASE WHEN l.part_id IS NULL THEN l.file_id END AS file_id,
                l.kind, f.screenshot_id AS image_id
            FROM links l JOIN storedfile f ON f.id = l.file_id
            WHERE l.kind IN ('mold','moldflow','scan') AND f.screenshot_id IS NOT NULL
        ), ranked AS (
            SELECT *, row_number() OVER (
                PARTITION BY part_id, file_id, kind ORDER BY image_id
            ) - 1 AS position FROM photos
        )
        INSERT INTO attachmentphoto (id, part_id, file_id, kind, position, image_id)
        SELECT gen_random_uuid(), part_id, file_id, kind, position, image_id
        FROM ranked WHERE position < 8
    """)


def downgrade() -> None:
    op.drop_table("attachmentphoto")
