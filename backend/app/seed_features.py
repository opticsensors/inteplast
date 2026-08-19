"""Carga de ejemplo de la base de conocimiento: el Bolt Eye del 3212.

Contenido sacado de `docs/modelo-datos.md` y `docs/3212/historial-molde.md`.
No se ejecuta en el arranque: es opcional y se lanza a mano.

    docker compose exec backend python -m app.seed_features
"""

import logging

from sqlmodel import Session, select

from app.core.db import engine
from app.models import (
    AssetKind,
    Feature,
    FeatureAsset,
    FeatureCategory,
    FeatureNote,
    NoteKind,
    Part,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOLT_EYE_WARNINGS = [
    (
        "Ubicacion del punto de inyeccion",
        "Se decide en Moldflow con cuatro variables: numero de puntos, posicion, "
        "tipo y diametro. Es lo primero que condiciona el resultado del agujero.",
    ),
    (
        "Sin lineas de soldadura en la zona del agujero",
        "Nota explicita del plano 2D. Se valida en el estudio de Moldflow antes "
        "de cerrar el molde.",
    ),
    (
        "Tolerancia dimensional del diametro",
        "En el 3212 es **O4 -0,1** (N170). Ojo: en el 3197 el mismo agujero lleva "
        "**O4 +0,1**, tolerancia inversa. Misma geometria, reglas distintas.",
    ),
    (
        "Tolerancia de posicion en el espacio",
        "N117, posicion 0,15 respecto de A-B para cada uno de los cuatro bolts. "
        "En el 3197 es 0,25 con MMC.",
    ),
    (
        "Depende de la planitud de la cara de referencia",
        "N178, planitud 0,10 del plano A. El plano A es la referencia de "
        "alineacion: tocandolo, la cota puede pasar de OK a NOK sin que el "
        "agujero cambie.",
    ),
    (
        "Conicidad y angulo de desmoldeo",
        "Por eso el diametro se mide a dos alturas, H = 1,5 mm y H = 5,0 mm. Si "
        "solo se mide una, la conicidad pasa desapercibida.",
    ),
    (
        "Fuerza de insercion del pin",
        "N288, entre 15 N y 50 N. Es la consecuencia funcional del diametro: el "
        "agujero puede estar en tolerancia y aun asi fallar el montaje.",
    ),
    (
        "Cambios de seccion y contracciones disimilares",
        "El problema de fondo en piezas no simetricas. La contraccion arrastra "
        "la posicion del agujero.",
    ),
]

BOLT_EYE_LESSONS = [
    (
        "Retoque de molde 1.33 sobre N170 (correccion 1)",
        "Se actuo sobre el macho del bolt segun la desviacion medida en el "
        "muestreo. La cota volvio a tolerancia en el muestreo siguiente: es el "
        "par antes/despues que demuestra que el retoque funciono. "
        "Ver `docs/3212/historial-molde.md`.",
    ),
    (
        "Tocar el plano A arrastra el resto de cotas",
        "De las diapositivas de correccion: *si tocamos 0,29 mm en el plano A, "
        "hay que tocar aqui 0,27*. Las cotas estan acopladas; no se retoca una "
        "sola cosa.",
    ),
]

# Los ficheros del 3212, uno por tipo. Ver docs/3212/README.md.
BOLT_EYE_ASSETS = [
    (AssetKind.mold, "Molde 3212 (STEP, 247 MB)"),
    (AssetKind.part, "Pieza 3212 (STP)"),
    (AssetKind.scan, "Escaneo de la pieza real (STL, lote 315346)"),
    (AssetKind.drawing, "Plano 2D rev. 07 (PDF)"),
    (AssetKind.moldflow, "Estudio Moldflow (MFR)"),
]


def seed(session: Session) -> None:
    existing = session.exec(select(Feature).where(Feature.name == "Bolt Eye")).first()
    if existing:
        logger.info("El feature 'Bolt Eye' ya existe, no se toca nada")
        return

    feature = Feature(
        name="Bolt Eye",
        description=(
            "Agujero pasante de los cuatro bolts. Agrupa N170 (diametro), N117 "
            "(posicion), N178 (planitud del plano A de referencia) y N288 "
            "(fuerza de insercion del pin)."
        ),
        category=FeatureCategory.hole,
        tags=["3212", "Pump Housing", "N170", "N117", "N178", "N288", "Bosch"],
    )
    session.add(feature)
    session.commit()
    session.refresh(feature)

    for position, (title, body) in enumerate(BOLT_EYE_WARNINGS):
        session.add(
            FeatureNote(
                feature_id=feature.id,
                kind=NoteKind.warning,
                title=title,
                body=body,
                position=position,
            )
        )
    for position, (title, body) in enumerate(BOLT_EYE_LESSONS):
        session.add(
            FeatureNote(
                feature_id=feature.id,
                kind=NoteKind.lesson,
                title=title,
                body=body,
                position=position,
            )
        )
    part = session.exec(select(Part).where(Part.code == "3212")).first()
    if not part:
        part = Part(code="3212", name="Pump Housing")
        session.add(part)
        session.commit()
        session.refresh(part)

    # El feature esta declarado en la pieza aunque no haya ficheros subidos.
    feature.parts.append(part)
    session.add(feature)

    # Sin fichero adjunto: los CAD del cliente no se copian al repo. Se suben
    # desde la propia aplicacion cuando haga falta.
    for position, (kind, name) in enumerate(BOLT_EYE_ASSETS):
        session.add(
            FeatureAsset(
                feature_id=feature.id,
                kind=kind,
                name=name,
                part_id=part.id,
                position=position,
            )
        )
    session.commit()
    logger.info("Feature 'Bolt Eye' creado")


def main() -> None:
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
