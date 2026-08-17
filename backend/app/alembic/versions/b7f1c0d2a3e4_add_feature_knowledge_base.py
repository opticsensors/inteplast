"""Add feature knowledge base (features, notes, assets, stored files)

Revision ID: b7f1c0d2a3e4
Revises: fe56fa70289e
Create Date: 2026-08-14 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b7f1c0d2a3e4'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'storedfile',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('content_type', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'feature',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column('category', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_id', sa.Uuid(), nullable=True),
        sa.Column('image_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['storedfile.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feature_category'), 'feature', ['category'], unique=False)
    op.create_index(op.f('ix_feature_name'), 'feature', ['name'], unique=False)
    op.create_table(
        'featurenote',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('body', sqlmodel.sql.sqltypes.AutoString(length=20000), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('feature_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['feature_id'], ['feature.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'featureasset',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('part_ref', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('feature_id', sa.Uuid(), nullable=False),
        sa.Column('file_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['feature_id'], ['feature.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['storedfile.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_featureasset_part_ref'), 'featureasset', ['part_ref'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_featureasset_part_ref'), table_name='featureasset')
    op.drop_table('featureasset')
    op.drop_table('featurenote')
    op.drop_index(op.f('ix_feature_name'), table_name='feature')
    op.drop_index(op.f('ix_feature_category'), table_name='feature')
    op.drop_table('feature')
    op.drop_table('storedfile')
