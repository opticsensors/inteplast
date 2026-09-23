"""Allowlisted reads of application data; never arbitrary SQL, URLs or files."""

import re
import uuid
from collections.abc import Sequence
from typing import Any, Literal, TypeVar
from urllib.parse import urlencode

from fastapi import HTTPException
from pydantic import Field, ValidationError, field_validator
from sqlalchemy import text
from sqlmodel import Session, col, func, select

from app import measurement_imports
from app.api.routes.catalog import search_catalog
from app.assistant.config import AssistantSettings, get_settings
from app.assistant.corrections import plan_evidence, recorded_limits
from app.assistant.retrieval import (
    correction_question,
    initial_read,
    name_score,
    normalize,
    part_read,
)
from app.assistant.schemas import ChatMessage, ChatRequest, Source, StrictModel
from app.assistant.summaries import measurements, page
from app.core.db import engine
from app.feature_links import feature_membership
from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic
from app.models import Feature, FeatureNote, Part, User

Entity = TypeVar("Entity", Part, Feature)


class Search(StrictModel):
    query: str = Field(
        default="",
        max_length=120,
        description="Nombre, código o palabra clave; vacío lista el catálogo.",
    )
    offset: int = Field(default=0, ge=0, le=10000)


class FeatureRead(StrictModel):
    feature_id: uuid.UUID = Field(
        description="UUID del feature devuelto por search_catalog; nunca su nombre."
    )
    offset: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Desplazamiento de notas; hasta 20 por lectura.",
    )


class PartRead(StrictModel):
    part: str = Field(
        min_length=1,
        max_length=64,
        description="Código de pieza (p. ej. 3212) o UUID devuelto por search_catalog. También admite un nombre inequívoco.",
    )
    feature_id: uuid.UUID | None = Field(
        default=None,
        description="UUID del feature solicitado; comprueba su vínculo con la pieza y la cota.",
    )
    section: Literal["overview", "measurements", "corrections"] = "overview"
    characteristic: str | None = Field(
        default=None,
        max_length=64,
        description="Cota, p. ej. N170. Omitir para listar.",
    )
    revision: str | None = Field(
        default=None,
        max_length=32,
        description="Revisión exacta; omitir usa la última disponible.",
    )
    snapshot_id: uuid.UUID | None = None
    sample: str | None = Field(default=None, max_length=64)
    cavity: str | None = Field(default=None, max_length=64)
    offset: int = Field(default=0, ge=0, le=10000)
    summary_offset: int = Field(default=0, ge=0, le=10000)
    include_rows: bool = False
    include_statistics: bool = False

    @field_validator("sample")
    @classmethod
    def normalize_sample(cls, value: str | None) -> str | None:
        if value:
            value = re.sub(r"^intern[.\s]*", "", value, flags=re.I)
            if value.isdigit():
                return value.zfill(2)
        return value

    @field_validator("cavity")
    @classmethod
    def normalize_cavity(cls, value: str | None) -> str | None:
        if value:
            value = re.sub(r"^c(?:avidad)?\s*", "", value, flags=re.I)
            if value.isdigit():
                return f"c{int(value)}"
        return value


class KnowledgeSearch(StrictModel):
    query: str = Field(min_length=1, max_length=3000)
    part: str | None = Field(default=None, max_length=64)
    feature_id: uuid.UUID | None = None
    revision: str | None = Field(default=None, max_length=32)
    characteristic: str | None = Field(default=None, max_length=64)


TOOL_MODELS: dict[str, type[StrictModel]] = {
    "search_catalog": Search,
    "read_feature": FeatureRead,
    "read_part": PartRead,
    "search_knowledge": KnowledgeSearch,
}
TOOL_LABELS = {
    "search_catalog": "Buscando en el catálogo…",
    "read_feature": "Consultando notas y piezas del feature…",
    "read_part": "Consultando datos de la pieza…",
    "search_knowledge": "Buscando conocimiento relacionado…",
}
DESCRIPTIONS = {
    "search_catalog": "Busca piezas, features y cotas en el catálogo real. Usa palabras clave cortas, no la pregunta completa.",
    "read_feature": "Lee descripción, warnings y lessons learned de un feature y sus piezas/cotas vinculadas.",
    "read_part": "Lee una pieza: overview, measurements (resumen COMPLETO y tolerancias) o corrections (texto PPTX). Filtra por cota/revisión/muestreo/cavidad. include_statistics=true añade mínimos/máximos/medias por serie; include_rows=true añade registros individuales. offset pagina filas, summary_offset pagina series.",
    "search_knowledge": "Busca por significado y palabras en descripciones, advertencias, lecciones y retoques importados. Usa una pregunta natural. Permite acotar pieza, feature, revisión y cota. No calcula mediciones ni enumera todas las notas.",
}


def definitions() -> list[dict[str, Any]]:
    # Omit cosmetic titles, but retain the contract the model needs to call tools.
    def parameters(model: type[StrictModel]) -> dict[str, Any]:
        schema = model.model_json_schema()
        properties = {}
        for name, field in schema["properties"].items():
            kind = field.get("anyOf", [field])[0]
            properties[name] = {k: v for k, v in kind.items() if k != "title"}
            for key in ("description", "default"):
                if key in field and field[key] is not None:
                    properties[name][key] = field[key]
        return {
            "type": "object",
            "properties": properties,
            "required": schema.get("required", []),
            "additionalProperties": False,
        }

    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": DESCRIPTIONS[name],
                "parameters": parameters(model),
            },
        }
        for name, model in TOOL_MODELS.items()
    ]


def clipped(value: str | None, size: int = 1000) -> str:
    value = value or ""
    return value if len(value) <= size else value[:size] + " [texto recortado]"


def provenance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    # Display provenance, never disclose filesystem roots or signed URLs.
    result = {
        k: clipped(str(value[k]), 160)
        for k in ("locator", "sheet", "row")
        if value.get(k) is not None
    }
    if value.get("path"):
        result["document"] = (
            str(value["path"]).replace("\\", "/").rsplit("/", 1)[-1][:180]
        )
    return result


class KnowledgeTools:
    def __init__(
        self, user_id: uuid.UUID, settings: AssistantSettings | None = None
    ) -> None:
        self.user_id = user_id
        self.settings = settings or get_settings()
        self.sources: dict[str, Source] = {}
        self.scope: dict[str, Any] = {}
        self.scope_error: dict[str, Any] | None = None

    def initial_lookup(self, question: str) -> tuple[str, dict[str, Any]] | None:
        """Ground the current question before letting history or catalog order steer it."""
        self.scope = {}
        self.scope_error = None
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            user = session.get(User, self.user_id)
            if user is None or not user.is_active:
                raise HTTPException(403, "La sesión ya no está activa.")
            parts = self.named(session.exec(select(Part)).all(), question, codes=True)
            features = self.named(session.exec(select(Feature)).all(), question)
            # Comparisons need multiple scopes; never silently collapse them to one.
            if re.search(r"compar|diferencia|\bentre\b", normalize(question)):
                return None
            if len(parts) > 1 or len(features) > 1:
                labels = [f"{p.code} · {p.name}" for p in parts] + [
                    f.name for f in features
                ]
                self.scope_error = {
                    "error": "La consulta coincide con varias fichas: "
                    + ", ".join(labels)
                    + ". Indica el código de pieza o el nombre exacto del feature.",
                    "error_code": "ambiguous_entity",
                    "retryable": False,
                }
                return "search_catalog", {"query": question[:120]}
            seed = initial_read(
                ChatRequest(messages=[ChatMessage(role="user", content=question)])
            )
            if seed is None and len(parts) == 1:
                seed = part_read(question, parts[0].code)
            if seed:
                name, arguments = seed
                if features:
                    arguments["feature_id"] = str(features[0].id)
                self.scope = {
                    k: v
                    for k, v in arguments.items()
                    if k in {"part", "feature_id", "characteristic", "revision"}
                }
                return name, arguments
            if features:
                self.scope["feature_id"] = str(features[0].id)
                # A feature can span multiple pieces: only infer one when unique.
                if correction_question(question) or re.search(
                    r"\bN\d+", question, re.I
                ):
                    links = feature_membership()
                    linked = session.exec(
                        select(Part).where(
                            col(Part.id).in_(
                                select(links.c.part_id).where(
                                    links.c.feature_id == features[0].id
                                )
                            )
                        )
                    ).all()
                    if len(linked) == 1:
                        seed = part_read(question, linked[0].code)
                        if seed:
                            seed[1]["feature_id"] = str(features[0].id)
                            self.scope.update(
                                {
                                    k: v
                                    for k, v in seed[1].items()
                                    if k in {"part", "characteristic", "revision"}
                                }
                            )
                            return seed
                return "read_feature", {"feature_id": str(features[0].id)}
        cotas = {c.upper() for c in re.findall(r"\bN\d+(?:\.\d+)?\b", question, re.I)}
        if len(cotas) == 1:
            self.scope["characteristic"] = next(iter(cotas))
        if re.search(
            r"advertenc|lecci[oó]n|contracci[oó]n|problema|retoque|riesgo|experiencia",
            question,
            re.I,
        ):
            return "search_knowledge", {"query": question}
        return None

    @staticmethod
    def named(
        records: Sequence[Entity], query: str, *, codes: bool = False
    ) -> list[Entity]:
        scored = [
            (
                r,
                max(
                    name_score(query, r.name or ""),
                    2.0
                    * float(
                        bool(
                            codes
                            and isinstance(r, Part)
                            and re.search(
                                r"(?<!\w)" + re.escape(r.code) + r"(?!\w)", query, re.I
                            )
                        )
                    ),
                ),
            )
            for r in records
        ]
        best = max((s for _, s in scored), default=0)
        return [r for r, s in scored if s == best and s > 0]

    def resolve_part(self, session: Session, value: str) -> Part | dict[str, Any]:
        try:
            part = session.get(Part, uuid.UUID(value))
        except ValueError:
            part = session.exec(select(Part).where(Part.code == value)).first()
        if part is not None:
            return part
        matches = self.named(session.exec(select(Part)).all(), value)
        if len(matches) == 1:
            return matches[0]
        return {
            "error": "No se ha identificado una pieza única con ese identificador. Esto no demuestra que falten datos ni correcciones.",
            "error_code": "ambiguous_part" if matches else "unresolved_part",
            "retryable": True,
            "recovery": "Busca la pieza con search_catalog y usa su code o id; si hay varias, pide aclaración.",
            "candidates": [{"code": p.code, "name": p.name} for p in matches],
        }

    def cite(self, label: str, url: str) -> None:
        if len(self.sources) < 12:
            self.sources[url] = Source(label=label, url=url)

    def run(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        model = TOOL_MODELS.get(name)
        if model is None:
            return {
                "error": "Herramienta no disponible. Solo se permiten las lecturas indicadas."
            }
        try:
            args = model.model_validate(arguments)
        except ValidationError:
            return {
                "error": "Parámetros inválidos. Revisa el esquema de la herramienta; no implica ausencia de datos.",
                "error_code": "invalid_arguments",
                "retryable": True,
                "recovery": "Usa los identificadores de search_catalog y vuelve a consultar.",
            }
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            # Recheck each call, including users disabled during a conversation.
            user = session.get(User, self.user_id)
            if user is None or not user.is_active:
                raise HTTPException(403, "La sesión ya no está activa.")
            if self.scope_error:
                return self.scope_error
            if isinstance(args, (PartRead, KnowledgeSearch)):
                if args.part:
                    resolved = self.resolve_part(session, args.part)
                    if isinstance(resolved, dict):
                        return resolved
                    args.part = resolved.code
                for key in ("part", "feature_id", "characteristic", "revision"):
                    expected, actual = self.scope.get(key), getattr(args, key)
                    if (
                        expected is not None
                        and actual is not None
                        and normalize(str(expected)) != normalize(str(actual))
                    ):
                        return {
                            "error": "La consulta cambia la pieza, el feature, la cota o la revisión solicitados.",
                            "error_code": "scope_mismatch",
                            "retryable": True,
                            "required_scope": self.scope,
                        }
                    if expected is not None:
                        setattr(
                            args,
                            key,
                            uuid.UUID(expected) if key == "feature_id" else expected,
                        )
            if (
                isinstance(args, FeatureRead)
                and self.scope.get("feature_id")
                and str(args.feature_id) != self.scope["feature_id"]
            ):
                return {
                    "error": "Ese feature no es el solicitado en la pregunta actual.",
                    "error_code": "scope_mismatch",
                    "retryable": True,
                    "required_scope": self.scope,
                }
            # Same shared, authenticated knowledge access as the existing APIs.
            # This is the only integration boundary to update if row ACLs are added.
            try:
                if isinstance(args, Search):
                    return self.search(session, user, args)
                if isinstance(args, FeatureRead):
                    return self.feature(session, args)
                if isinstance(args, PartRead):
                    return self.part(session, args)
                if isinstance(args, KnowledgeSearch):
                    from app.assistant.semantic import search

                    result = search(session, args, self.settings)
                    for hit in result["hits"]:
                        self.cite(hit["title"], hit["url"])
                    return result
            except HTTPException as error:
                if error.status_code == 404:
                    return {
                        "error": "No se ha podido recuperar el registro con esos identificadores; no demuestra que no exista el feature o la corrección.",
                        "error_code": "unresolved_record",
                        "retryable": True,
                        "recovery": "Comprueba código/UUID, revisión y snapshot; localiza la ficha con search_catalog y reintenta.",
                    }
                raise
        return {"error": "Lectura no disponible."}

    def search(self, session: Session, user: User, args: Search) -> dict[str, Any]:
        features = self.named(session.exec(select(Feature)).all(), args.query)
        parts = self.named(session.exec(select(Part)).all(), args.query, codes=True)
        feature_id = (
            uuid.UUID(self.scope["feature_id"])
            if self.scope.get("feature_id")
            else (features[0].id if len(features) == 1 else None)
        )
        part = (
            self.resolve_part(session, self.scope["part"])
            if self.scope.get("part")
            else (parts[0] if len(parts) == 1 else None)
        )
        cotas = re.findall(r"\bN\d+(?:\.\d+)?\b", args.query, re.I)
        query = self.scope.get("characteristic") or (
            cotas[0].upper()
            if len(cotas) == 1
            else (
                features[0].name
                if len(features) == 1
                else (part.code if isinstance(part, Part) else args.query)
            )
        )
        result = search_catalog(
            session,
            user,
            q=query,
            part_id=part.id if isinstance(part, Part) else None,
            feature_id=feature_id,
            skip=args.offset,
            limit=5,
        )
        for found_part in result.parts:
            self.cite(f"Pieza {found_part.code}", f"/parts/{found_part.id}")
        for feature in result.features:
            self.cite(feature.name, f"/features/{feature.id}")
        for cota in result.cotas:
            self.cite(
                f"{cota.part.code} · {cota.code} · rev. {cota.revision}",
                f"/parts/{cota.part.id}?{urlencode({'cota': cota.code, 'revision': cota.revision})}",
            )
        return {
            "parts": [
                {"id": str(p.id), "code": p.code, "name": p.name} for p in result.parts
            ],
            "features": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "description": clipped(f.description, 350),
                }
                for f in result.features
            ],
            "characteristics": [
                {
                    "code": c.code,
                    "title": c.title,
                    "revision": c.revision,
                    "part": c.part.code,
                }
                for c in result.cotas
            ],
            "totals": {
                "parts": result.part_count,
                "features": result.feature_count,
                "characteristics": result.cota_count,
            },
            "offset": args.offset,
            "page_size": 5,
            "coverage": {
                "parts": page(result.part_count, args.offset, len(result.parts)),
                "features": page(
                    result.feature_count, args.offset, len(result.features)
                ),
                "characteristics": page(
                    result.cota_count, args.offset, len(result.cotas)
                ),
            },
        }

    def feature(self, session: Session, args: FeatureRead) -> dict[str, Any]:
        feature = session.get(Feature, args.feature_id)
        if not feature:
            raise HTTPException(404)
        self.cite(feature.name, f"/features/{feature.id}")
        notes = session.exec(
            select(FeatureNote)
            .where(FeatureNote.feature_id == feature.id)
            .order_by(col(FeatureNote.position), col(FeatureNote.id))
            .offset(args.offset)
            .limit(20)
        ).all()
        total = session.exec(
            select(func.count())
            .select_from(FeatureNote)
            .where(FeatureNote.feature_id == feature.id)
        ).one()
        links = feature_membership()
        parts = session.exec(
            select(Part)
            .where(
                col(Part.id).in_(
                    select(links.c.part_id).where(links.c.feature_id == feature.id)
                )
            )
            .order_by(Part.code)
            .limit(11)
        ).all()
        cotas = session.exec(
            select(PartCharacteristic)
            .join(FeatureCharacteristicLink)
            .where(FeatureCharacteristicLink.feature_id == feature.id)
            .order_by(PartCharacteristic.code, PartCharacteristic.revision)
            .limit(21)
        ).all()
        return {
            "name": feature.name,
            "description": feature.description,
            "notes": [
                {
                    "kind": n.kind,
                    "title": n.title,
                    "body": clipped(n.body, 1600),
                    "body_truncated": len(n.body or "") > 1600,
                }
                for n in notes
            ],
            "notes_total": total,
            "offset": args.offset,
            "page_size": 20,
            "coverage": {"notes": page(total, args.offset, len(notes))},
            "parts": [
                {"id": str(p.id), "code": p.code, "name": p.name} for p in parts[:10]
            ],
            "characteristics": [
                {
                    "code": c.code,
                    "title": c.title,
                    "revision": c.revision,
                    "part_id": str(c.part_id),
                }
                for c in cotas[:20]
            ],
            "links_truncated": len(parts) > 10 or len(cotas) > 20,
        }

    def part(self, session: Session, args: PartRead) -> dict[str, Any]:
        part = self.resolve_part(session, args.part)
        if isinstance(part, dict):
            return part
        job, revisions = measurement_imports.study(
            session, part, args.revision, args.snapshot_id
        )
        payload = job.payload
        revision = payload.get("measurement_revision") or args.revision
        query = {
            k: str(v)
            for k, v in {
                "revision": revision,
                "snapshot": args.snapshot_id,
                "cota": args.characteristic,
            }.items()
            if v
        }
        self.cite(
            f"Pieza {part.code}" + (f" · rev. {revision}" if revision else ""),
            f"/parts/{part.id}" + (f"?{urlencode(query)}" if query else ""),
        )
        result: dict[str, Any] = {
            "part": part.code,
            "name": part.name,
            "revision": revision,
            "available_revisions": revisions,
            "import_state": job.state,
        }
        characteristic = (args.characteristic or "").strip().upper().replace(" ", "")
        if characteristic and characteristic[0].isdigit():
            characteristic = "N" + characteristic
        allowed_characteristics: set[str] | None = None
        if args.feature_id:
            feature = session.get(Feature, args.feature_id)
            links = feature_membership()
            linked = session.exec(
                select(links.c.part_id).where(
                    links.c.feature_id == args.feature_id, links.c.part_id == part.id
                )
            ).first()
            cota_filters = [
                FeatureCharacteristicLink.feature_id == args.feature_id,
                PartCharacteristic.part_id == part.id,
            ]
            if characteristic:
                cota_filters.append(PartCharacteristic.code == characteristic)
            if revision:
                cota_filters.append(PartCharacteristic.revision == revision)
            cota_links = session.exec(
                select(PartCharacteristic)
                .join(FeatureCharacteristicLink)
                .where(*cota_filters)
            ).all()
            if feature is None or linked is None or (characteristic and not cota_links):
                return {
                    "error": "No hay un vínculo explícito registrado entre el feature, la pieza y la cota/revisión solicitados. No significa que esas fichas o sus correcciones no existan.",
                    "error_code": "unverified_relationship",
                    "retryable": False,
                }
            result["feature"] = feature.name
            allowed_characteristics = {c.code for c in cota_links}
        result["filters"] = {
            "characteristic": characteristic or None,
            "sample": args.sample,
            "cavity": args.cavity,
        }
        entries = [
            e
            for e in payload.get("catalog", {}).get("entries", [])
            if not characteristic
            or characteristic in e.get("numbers", [])
            or e["id"] == characteristic
        ]
        if allowed_characteristics is not None:
            entries = [
                e
                for e in entries
                if allowed_characteristics.intersection(
                    [e["id"], *e.get("numbers", [])]
                )
            ]
        if args.section == "overview":
            filters: list[Any] = [PartCharacteristic.part_id == part.id]
            if allowed_characteristics is not None:
                filters.append(
                    col(PartCharacteristic.code).in_(allowed_characteristics)
                )
            if revision:
                filters.append(PartCharacteristic.revision == revision)
            if characteristic:
                filters.append(PartCharacteristic.code == characteristic)
            cotas = session.exec(
                select(PartCharacteristic)
                .where(*filters)
                .order_by(PartCharacteristic.code, PartCharacteristic.revision)
                .offset(args.offset)
                .limit(6)
            ).all()
            cota_count = session.exec(
                select(func.count()).select_from(PartCharacteristic).where(*filters)
            ).one()
            links = feature_membership()
            features = session.exec(
                select(Feature)
                .where(
                    col(Feature.id).in_(
                        select(links.c.feature_id).where(links.c.part_id == part.id)
                    )
                )
                .order_by(Feature.name)
                .limit(11)
            ).all()
            result.update(
                {
                    "features": [
                        {"id": str(f.id), "name": f.name} for f in features[:10]
                    ],
                    "features_truncated": len(features) > 10,
                    "characteristics": [
                        {
                            "code": c.code,
                            "title": c.title,
                            "revision": c.revision,
                        }
                        for c in cotas
                    ],
                    "total": cota_count,
                    "offset": args.offset,
                    "page_size": 6,
                    "coverage": {
                        "characteristics": page(cota_count, args.offset, len(cotas))
                    },
                    "samples": payload.get("samples", [])[:30],
                    "cavities": payload.get("cavities", [])[:20],
                }
            )
        elif args.section == "measurements":
            summary, aggregates, all_rows = measurements(
                entries, cavity=args.cavity, sample=args.sample
            )
            rows = all_rows[args.offset : args.offset + 8]
            groups = aggregates[args.summary_offset : args.summary_offset + 20]
            columns = [
                "characteristic",
                "series_id",
                "series",
                "unit",
                "nominal",
                "lower",
                "upper",
                "count",
                "min",
                "max",
                "mean",
                "status_counts",
            ]
            result.update(
                {
                    "total": summary["total"],
                    "status_counts": summary["status_counts"],
                    "summary": summary,
                    "series_index": [
                        f"{g['characteristic']} · {g['series']}" for g in groups
                    ],
                    "coverage": {
                        "series_index": page(
                            len(aggregates), args.summary_offset, len(groups)
                        ),
                    },
                    "offset": args.offset,
                    "page_size": 8,
                }
            )
            if args.include_statistics:
                # Numerical details are opt-in so general questions don't focus
                # on the first series instead of the whole study.
                result["series_columns"] = columns
                result["series_summaries"] = [
                    [g[column] for column in columns] for g in groups
                ]
                result["coverage"]["series_summaries"] = page(
                    len(aggregates), args.summary_offset, len(groups)
                )
            if args.include_rows or args.offset or (args.cavity and args.sample):
                result["rows"] = rows
                result["coverage"]["rows"] = page(len(all_rows), args.offset, len(rows))
        else:
            actions = [
                a
                for a in payload.get("action_index", {}).values()
                if not characteristic or characteristic in a.get("features", [])
            ]
            if allowed_characteristics is not None:
                actions = [
                    a
                    for a in actions
                    if allowed_characteristics.intersection(a.get("features", []))
                ]
            action_characteristics = {
                code for action in actions for code in action.get("features", [])
            }
            limit_entries = [
                entry
                for entry in entries
                if action_characteristics.intersection(
                    [entry["id"], *entry.get("numbers", [])]
                )
            ]
            limits = recorded_limits(
                limit_entries, cavity=args.cavity, sample=args.sample
            )
            limit_page = limits[args.summary_offset : args.summary_offset + 8]
            result.update(
                {
                    "actions": [
                        plan_evidence(a) for a in actions[args.offset : args.offset + 4]
                    ],
                    "recorded_limits": limit_page,
                    "limits_basis": "Límites de las cotas en las mediciones importadas de esta revisión. No son dimensiones de herramientas ni cantidades del retoque inferidas del título del plan.",
                    "total": len(actions),
                    "offset": args.offset,
                    "page_size": 4,
                    "coverage": {
                        "actions": page(
                            len(actions),
                            args.offset,
                            len(actions[args.offset : args.offset + 4]),
                        ),
                        "recorded_limits": page(
                            len(limits), args.summary_offset, len(limit_page)
                        ),
                    },
                    "notice": "Son planes/textos importados, no prueba de ejecución del retoque ni de conformidad final. No se han analizado imágenes o geometría.",
                }
            )
        return result
