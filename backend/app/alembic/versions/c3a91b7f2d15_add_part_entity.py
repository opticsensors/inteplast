"""Add part entity: group feature assets by piece, link feature to piece

Crea la tabla `part` (la pieza = el proyecto = el molde, identificada por su
numero de 4 digitos), sustituye el texto libre `featureasset.part_ref` por una
FK a esa tabla, y anade `featurepartlink` para declarar que un feature aparece
en una pieza aunque todavia no tenga ficheros.

El backfill saca el codigo de los `part_ref` existentes y conserva el resto del
texto en el nombre del adjunto cuando no cabe en el nombre de la pieza.

Revision ID: c3a91b7f2d15
Revises: b7f1c0d2a3e4
Create Date: 2026-08-18 12:00:00.000000

"""
import re
import uuid
from collections import Counter, defaultdict

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c3a91b7f2d15'
down_revision = 'b7f1c0d2a3e4'
branch_labels = None
depends_on = None


# "3212 Pump Housing" -> ("3212", "Pump Housing"). El codigo de proyecto son
# 4 digitos, pero se aceptan 3 a 5 por si acaso.
CODE_RE = re.compile(r'^\s*(\d{3,5})\b[\s.\-_]*(.*)$')

# Nombres que delatan un escaneo de la pieza real y no el CAD nominal. Solo se
# aplica a los adjuntos que ya eran de tipo 'part': el tipo 'scan' no existia.
SCAN_RE = re.compile(r'escane|scan|\.stl|\bstl\b', re.IGNORECASE)


def _split(part_ref):
    """part_ref libre -> (codigo, resto del texto)."""
    match = CODE_RE.match(part_ref)
    if match:
        return match.group(1), match.group(2).strip()
    return part_ref.strip(), ''


def upgrade():
    op.create_table(
        'part',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_part_code'), 'part', ['code'], unique=True)

    op.create_table(
        'featurepartlink',
        sa.Column('feature_id', sa.Uuid(), nullable=False),
        sa.Column('part_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['feature_id'], ['feature.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['part_id'], ['part.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('feature_id', 'part_id'),
    )

    op.add_column('featureasset', sa.Column('part_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'featureasset_part_id_fkey',
        'featureasset',
        'part',
        ['part_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        op.f('ix_featureasset_part_id'), 'featureasset', ['part_id'], unique=False
    )

    _backfill_parts()

    op.drop_index(op.f('ix_featureasset_part_ref'), table_name='featureasset')
    op.drop_column('featureasset', 'part_ref')


def _backfill_parts():
    """Crea una pieza por codigo y engancha los adjuntos que la referenciaban."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            'SELECT id, name, part_ref FROM featureasset '
            "WHERE part_ref IS NOT NULL AND btrim(part_ref) <> ''"
        )
    ).fetchall()
    if not rows:
        return

    # Un solo nombre por codigo: gana el que mas veces aparece.
    names_by_code = defaultdict(Counter)
    for _, _, part_ref in rows:
        code, rest = _split(part_ref)
        if rest:
            names_by_code[code][rest] += 1

    codes = []
    for _, _, part_ref in rows:
        code, _rest = _split(part_ref)
        if code not in codes:
            codes.append(code)

    part_ids = {}
    chosen_names = {}
    for code in codes:
        counter = names_by_code.get(code)
        name = counter.most_common(1)[0][0] if counter else None
        part_ids[code] = uuid.uuid4()
        chosen_names[code] = name
        bind.execute(
            sa.text(
                'INSERT INTO part (id, code, name, created_at) '
                'VALUES (:id, :code, :name, now())'
            ),
            {'id': part_ids[code], 'code': code[:64], 'name': name[:255] if name else None},
        )

    for asset_id, asset_name, part_ref in rows:
        code, rest = _split(part_ref)
        # El texto que no cabe en la pieza ("lote 315346") se conserva pegado al
        # nombre del adjunto: es informacion del cliente y no hay otro sitio.
        new_name = asset_name
        if rest and rest != chosen_names.get(code) and rest.lower() not in asset_name.lower():
            new_name = '{} - {}'.format(asset_name, rest)[:255]
        bind.execute(
            sa.text(
                'UPDATE featureasset SET part_id = :part_id, name = :name '
                'WHERE id = :id'
            ),
            {'part_id': part_ids[code], 'name': new_name, 'id': asset_id},
        )

    # El tipo 'scan' no existia: los escaneos estaban metidos en 'part'.
    scan_rows = bind.execute(
        sa.text("SELECT id, name FROM featureasset WHERE kind = 'part'")
    ).fetchall()
    for asset_id, asset_name in scan_rows:
        if SCAN_RE.search(asset_name or ''):
            bind.execute(
                sa.text("UPDATE featureasset SET kind = 'scan' WHERE id = :id"),
                {'id': asset_id},
            )


def downgrade():
    op.add_column(
        'featureasset',
        sa.Column(
            'part_ref',
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
    )
    # Se reconstruye "codigo nombre"; no tiene por que ser el texto original.
    op.execute(
        'UPDATE featureasset SET part_ref = btrim(part.code || \' \' || '
        "coalesce(part.name, '')) FROM part WHERE featureasset.part_id = part.id"
    )
    op.execute("UPDATE featureasset SET kind = 'part' WHERE kind = 'scan'")
    op.execute("UPDATE featureasset SET kind = 'mold' WHERE kind = 'moldflow'")
    op.create_index(
        op.f('ix_featureasset_part_ref'), 'featureasset', ['part_ref'], unique=False
    )

    op.drop_index(op.f('ix_featureasset_part_id'), table_name='featureasset')
    op.drop_constraint('featureasset_part_id_fkey', 'featureasset', type_='foreignkey')
    op.drop_column('featureasset', 'part_id')

    op.drop_table('featurepartlink')
    op.drop_index(op.f('ix_part_code'), table_name='part')
    op.drop_table('part')
