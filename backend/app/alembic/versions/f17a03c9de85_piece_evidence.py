"""Piece characteristics, shared drawing review and durable evidence imports.

Revision ID: f17a03c9de85
Revises: f170a3c9de85
"""

import re
import uuid

import sqlalchemy as sa
from alembic import op

revision = "f17a03c9de85"
down_revision = "f170a3c9de85"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partcharacteristic",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "part_id",
            sa.Uuid(),
            sa.ForeignKey("part.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.UniqueConstraint("part_id", "code", "revision"),
    )
    op.create_index("ix_partcharacteristic_part_id", "partcharacteristic", ["part_id"])
    op.create_table(
        "featurecharacteristiclink",
        sa.Column(
            "feature_id",
            sa.Uuid(),
            sa.ForeignKey("feature.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "characteristic_id",
            sa.Uuid(),
            sa.ForeignKey("partcharacteristic.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(32), nullable=False),
    )
    op.create_table(
        "pendingcharacteristic",
        sa.Column(
            "feature_id",
            sa.Uuid(),
            sa.ForeignKey("feature.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(64), primary_key=True),
    )
    op.create_table(
        "partdocument",
        sa.Column(
            "part_id",
            sa.Uuid(),
            sa.ForeignKey("part.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "file_id",
            sa.Uuid(),
            sa.ForeignKey("storedfile.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
    )
    op.create_table(
        "evidencejob",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("part_id", sa.Uuid(), sa.ForeignKey("part.id", ondelete="CASCADE")),
        sa.Column(
            "file_id", sa.Uuid(), sa.ForeignKey("storedfile.id", ondelete="CASCADE")
        ),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("message", sa.String()),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidencejob_state", "evidencejob", ["state"])
    op.create_table(
        "drawinglocation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "file_id",
            sa.Uuid(),
            sa.ForeignKey("storedfile.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("candidate_id", sa.String(96), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("box", sa.JSON(), nullable=False),
        sa.Column(
            "reviewed_by", sa.Uuid(), sa.ForeignKey("user.id", ondelete="SET NULL")
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("file_id", "sha256", "candidate_id"),
    )
    op.create_index("ix_drawinglocation_file_id", "drawinglocation", ["file_id"])

    # Only the documented Bolt Eye/3212 association is inferred. Preserve all
    # other numeric tags as pending rather than assigning them to every piece.
    db = op.get_bind()
    part = db.execute(sa.text("SELECT id FROM part WHERE code='3212'")).scalar()
    for feature in (
        db.execute(sa.text("SELECT id,name,tags FROM feature")).mappings().all()
    ):
        numeric = {
            tag for tag in feature["tags"] if re.fullmatch(r"N\d+(?:\.\d+)?", tag)
        }
        for code in numeric:
            if (
                part
                and feature["name"] == "Bolt Eye"
                and code in {"N170", "N117", "N178", "N288"}
            ):
                cid = uuid.uuid4()
                db.execute(
                    sa.text(
                        "INSERT INTO partcharacteristic VALUES (:id,:part,:code,'06','') ON CONFLICT DO NOTHING"
                    ),
                    {"id": cid, "part": part, "code": code},
                )
                cid = db.execute(
                    sa.text(
                        "SELECT id FROM partcharacteristic WHERE part_id=:part AND code=:code AND revision='06'"
                    ),
                    {"part": part, "code": code},
                ).scalar()
                db.execute(
                    sa.text(
                        "INSERT INTO featurecharacteristiclink VALUES (:fid,:cid,:role)"
                    ),
                    {
                        "fid": feature["id"],
                        "cid": cid,
                        "role": "reference" if code == "N178" else "primary",
                    },
                )
            else:
                db.execute(
                    sa.text("INSERT INTO pendingcharacteristic VALUES (:fid,:code)"),
                    {"fid": feature["id"], "code": code},
                )
        if numeric:
            db.execute(
                sa.text("UPDATE feature SET tags=:tags WHERE id=:id"),
                {
                    "tags": [t for t in feature["tags"] if t not in numeric],
                    "id": feature["id"],
                },
            )


def downgrade():
    # Keep every migrated identifier if rolling the schema back.
    db = op.get_bind()
    for feature in db.execute(sa.text("SELECT id,tags FROM feature")).mappings().all():
        codes = (
            db.execute(
                sa.text(
                    "SELECT code FROM pendingcharacteristic WHERE feature_id=:id UNION SELECT c.code FROM partcharacteristic c JOIN featurecharacteristiclink l ON c.id=l.characteristic_id WHERE l.feature_id=:id"
                ),
                {"id": feature["id"]},
            )
            .scalars()
            .all()
        )
        db.execute(
            sa.text("UPDATE feature SET tags=:tags WHERE id=:id"),
            {
                "id": feature["id"],
                "tags": list(dict.fromkeys(feature["tags"] + list(codes))),
            },
        )
    for name in (
        "drawinglocation",
        "evidencejob",
        "partdocument",
        "pendingcharacteristic",
        "featurecharacteristiclink",
        "partcharacteristic",
    ):
        op.drop_table(name)
