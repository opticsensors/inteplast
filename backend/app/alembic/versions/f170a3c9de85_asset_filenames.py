"""Use the real document filename for existing linked asset labels.

Revision ID: f170a3c9de85
Revises: e06f92b8cd74
"""

from alembic import op

revision = "f170a3c9de85"
down_revision = "e06f92b8cd74"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE featureasset AS asset
        SET name = document.filename
        FROM storedfile AS document
        WHERE asset.file_id = document.id AND asset.name <> document.filename
    """)


def downgrade():
    # Data correction only; earlier code can display the real filenames too.
    pass
