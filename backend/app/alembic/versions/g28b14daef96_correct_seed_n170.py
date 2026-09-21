"""Correct only the unchanged example lesson that claimed N170 was resolved.

Revision ID: g28b14daef96
Revises: f17a03c9de85
"""
import sqlalchemy as sa
from alembic import op

revision = "g28b14daef96"
down_revision = "f17a03c9de85"
branch_labels = None
depends_on = None

OLD = (
    "Se actuo sobre el macho del bolt segun la desviacion medida en el "
    "muestreo. La cota volvio a tolerancia en el muestreo siguiente: es el "
    "par antes/despues que demuestra que el retoque funciono. "
    "Ver `docs/3212/historial-molde.md`."
)
NEW = (
    "La mejora entre intern.01 e intern.03 es parcial: hay que evaluar GX "
    "y LP máximo por separado, en cada cavidad y altura. El Excel guarda "
    "una previsión de +0,500 mm; el PowerPoint propone usar expulsores de "
    "Ø4. El marcador no confirma su ejecución ni acredita el cierre de "
    "N170. Consultar el caso N170 en Correcciones de la pieza 3212."
)


def upgrade():
    op.get_bind().execute(sa.text(
        "UPDATE featurenote SET body=:new WHERE body=:old "
        "AND title='Retoque de molde 1.33 sobre N170 (correccion 1)' "
        "AND feature_id IN (SELECT id FROM feature WHERE name='Bolt Eye')"
    ), {"old": OLD, "new": NEW})


def downgrade():
    # A schema rollback must not reintroduce the incorrect technical claim.
    pass
