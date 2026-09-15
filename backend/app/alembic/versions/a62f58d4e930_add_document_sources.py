"""Keep document identity separate from uploaded or external content.

Revision ID: a62f58d4e930
Revises: c3a91b7f2d15
"""
from alembic import op
import sqlalchemy as sa

revision = "a62f58d4e930"
down_revision = "c3a91b7f2d15"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("storedfile", sa.Column("source", sa.String(32), nullable=False, server_default="upload"))
    for name, length in [("source_key", 100), ("source_path", 2048), ("source_version", 100), ("revision", 100)]:
        op.add_column("storedfile", sa.Column(name, sa.String(length), nullable=True))
    op.add_column("storedfile", sa.Column("version", sa.Uuid(), nullable=True))
    op.add_column("storedfile", sa.Column("reference_key", sa.String(64), nullable=True))
    # Repeated selections reuse a document; concurrent selections cannot duplicate it.
    op.create_unique_constraint("storedfile_reference_key_key", "storedfile", ["reference_key"])


def downgrade():
    # Downgrading with references would turn them into missing uploads.
    if op.get_bind().execute(sa.text("SELECT count(*) FROM storedfile WHERE source <> 'upload'")).scalar():
        raise RuntimeError("Unlink external document records before downgrading this migration")
    op.drop_constraint("storedfile_reference_key_key", "storedfile", type_="unique")
    for name in ["reference_key", "version", "revision", "source_version", "source_path", "source_key", "source"]:
        op.drop_column("storedfile", name)
