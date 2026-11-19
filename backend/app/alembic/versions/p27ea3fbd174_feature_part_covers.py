"""Feature covers per piece: the capture moves to the feature-piece link.

1. `featurepartlink` gets `image_id` and `cover_3d` (same schema as `FeatureCover3D`).
2. Pieces that belonged to a feature only through an attachment get their link.
3. A CAD cover (`feature.cover_3d` with its `part_id`) moves with its image to the link
   of that piece, and the feature loses that image. `feature.cover_3d` is left as it was:
   it is no longer read, and the downgrade uses it to know which piece the cover was on.
4. A pasted image without piece stays as the feature image; the application shows it
   only while the feature has no pieces.

Going back restores, for each feature with a moved cover, the current cover of that same
piece. If that cover was removed, its piece unlinked or a new image pasted on the feature,
the old selection is dropped: it never comes back alone or beside another image. Covers made later on other pieces are lost, and
the links created in step 2 are kept: they only repeat what the attachments already said.

Revision ID: p27ea3fbd174
Revises: o16d92fa1c07
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op

revision = "p27ea3fbd174"
down_revision = "o16d92fa1c07"
branch_labels = None
depends_on = None

# A JSON column emptied from Python may hold JSON null instead of SQL NULL.
HAS_CAD = "f.cover_3d IS NOT NULL AND f.cover_3d::text <> 'null'"


def upgrade() -> None:
    op.add_column("featurepartlink", sa.Column("image_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "featurepartlink_image_id_fkey",
        "featurepartlink",
        "storedfile",
        ["image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("featurepartlink", sa.Column("cover_3d", sa.JSON(), nullable=True))

    op.execute(
        "INSERT INTO featurepartlink (feature_id, part_id) "
        "SELECT DISTINCT feature_id, part_id FROM featureasset "
        "WHERE part_id IS NOT NULL "
        "ON CONFLICT DO NOTHING"
    )
    op.execute(
        "UPDATE featurepartlink l SET image_id = f.image_id, cover_3d = f.cover_3d "
        "FROM feature f "
        f"WHERE l.feature_id = f.id AND f.image_id IS NOT NULL AND {HAS_CAD} "
        "AND l.part_id::text = f.cover_3d->>'part_id'"
    )
    op.execute(
        "UPDATE feature f SET image_id = NULL FROM featurepartlink l "
        f"WHERE l.feature_id = f.id AND {HAS_CAD} "
        "AND l.part_id::text = f.cover_3d->>'part_id' AND l.image_id = f.image_id"
    )


def downgrade() -> None:
    # `feature.cover_3d` is stale after migrating. Keep it only where the same piece
    # still has a cover that can come back with it: the feature has no image of its
    # own yet. Otherwise (cover removed, piece unlinked, or a new image pasted on the
    # feature) the old faces go: they must never sit beside another image.
    op.execute(
        f"UPDATE feature f SET cover_3d = NULL WHERE {HAS_CAD} AND NOT ("
        "f.image_id IS NULL AND EXISTS (SELECT 1 FROM featurepartlink l "
        "WHERE l.feature_id = f.id AND l.part_id::text = f.cover_3d->>'part_id' "
        "AND l.image_id IS NOT NULL))"
    )
    op.execute(
        "UPDATE feature f SET image_id = l.image_id, cover_3d = l.cover_3d "
        "FROM featurepartlink l "
        f"WHERE l.feature_id = f.id AND f.image_id IS NULL AND {HAS_CAD} "
        "AND l.part_id::text = f.cover_3d->>'part_id' AND l.image_id IS NOT NULL"
    )
    op.drop_column("featurepartlink", "cover_3d")
    op.drop_constraint(
        "featurepartlink_image_id_fkey", "featurepartlink", type_="foreignkey"
    )
    op.drop_column("featurepartlink", "image_id")
