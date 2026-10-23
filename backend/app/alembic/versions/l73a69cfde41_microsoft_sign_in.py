"""Microsoft sign-in: per-user token caches, pending logins and preview requester."""

import sqlalchemy as sa
from alembic import op

revision = "l73a69cfde41"
down_revision = "k62f58becd30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "microsoftaccount",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("object_id", sa.String(64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("token_cache", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "microsoftlogin",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("flow", sa.Text(), nullable=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        "filepreview",
        sa.Column(
            "requested_by",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("filepreview", "requested_by")
    op.drop_table("microsoftlogin")
    op.drop_table("microsoftaccount")
