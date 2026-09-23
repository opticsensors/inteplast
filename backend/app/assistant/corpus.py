"""Text already present in app records, with live scope and source metadata.

No repository documents, raw uploads, measurements or filesystem reads belong here.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from sqlmodel import Session, col, select

from app.feature_links import feature_membership
from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic
from app.measurement_imports import legacy_study
from app.models import Feature, FeatureNote, Part


@dataclass(frozen=True)
class Passage:
    id: str
    source_id: str
    title: str
    text: str
    url: str
    scope: dict[str, Any]

    @property
    def fingerprint(self) -> str:
        value = json.dumps(
            [self.title, self.text, self.url, self.scope], sort_keys=True
        )
        return hashlib.sha256(value.encode()).hexdigest()


def chunks(
    source_id: str, title: str, body: str, url: str, scope: dict[str, Any]
) -> list[Passage]:
    body = body.strip()
    if not body:
        return []
    result: list[Passage] = []
    start = 0
    while start < len(body):
        end = min(start + 1200, len(body))
        if end < len(body):
            boundary = body.rfind(" ", start + 800, end)
            if boundary > start:
                end = boundary
        result.append(
            Passage(
                f"{source_id}:{len(result)}",
                source_id,
                title,
                body[start:end],
                url,
                scope,
            )
        )
        if end == len(body):
            break
        start = end - 150
    return result


def collect(session: Session) -> list[Passage]:
    parts = {p.id: p for p in session.exec(select(Part)).all()}
    features = {f.id: f for f in session.exec(select(Feature)).all()}
    members: dict[str, list[str]] = {}
    membership = feature_membership()
    for part_id, feature_id in session.execute(
        select(membership.c.part_id, membership.c.feature_id)
    ).all():
        if part_id in parts:
            members.setdefault(str(feature_id), []).append(parts[part_id].code)
    links: dict[str, list[dict[str, str]]] = {}
    for link, cota in session.exec(
        select(FeatureCharacteristicLink, PartCharacteristic).join(PartCharacteristic)
    ).all():
        if cota.part_id in parts:
            links.setdefault(str(link.feature_id), []).append(
                {
                    "part": parts[cota.part_id].code,
                    "revision": cota.revision,
                    "characteristic": cota.code,
                }
            )

    def feature_scope(feature: Feature) -> dict[str, Any]:
        return {
            "feature_id": str(feature.id),
            "feature": feature.name,
            "parts": sorted(set(members.get(str(feature.id), []))),
            "links": sorted(
                links.get(str(feature.id), []), key=lambda x: tuple(x.values())
            ),
            "scope": "feature_general",
        }

    documents: list[Passage] = []
    for feature in features.values():
        documents.extend(
            chunks(
                f"feature:{feature.id}",
                feature.name,
                "\n".join([feature.name, feature.description or "", *feature.tags]),
                f"/features/{feature.id}",
                {**feature_scope(feature), "kind": "description"},
            )
        )
    for note in session.exec(select(FeatureNote).order_by(col(FeatureNote.id))).all():
        note_feature = features.get(note.feature_id)
        if note_feature:
            documents.extend(
                chunks(
                    f"note:{note.id}",
                    f"{note_feature.name} · {note.title}",
                    note.title + "\n" + (note.body or ""),
                    f"/features/{note_feature.id}",
                    {
                        **feature_scope(note_feature),
                        "kind": str(getattr(note.kind, "value", note.kind)),
                    },
                )
            )
    for part in parts.values():
        # Same current imported baseline used by read_part; no importer is run.
        payload = legacy_study(session, part.id)
        revision = payload.get("measurement_revision")
        for key, action in payload.get("action_index", {}).items():
            cotas = action.get("features", [])
            query = {"revision": revision} if revision else {}
            if len(cotas) == 1:
                query["cota"] = cotas[0]
            url = f"/parts/{part.id}" + ("?" + urlencode(query) if query else "")
            from app.assistant.tools import provenance

            documents.extend(
                chunks(
                    f"correction:{part.id}:{revision}:{key}",
                    f"{part.code} · {action.get('title') or key}",
                    "\n".join(action.get("paragraphs", [])),
                    url,
                    {
                        "kind": "correction_plan",
                        "parts": [part.code],
                        "revision": revision,
                        "characteristics": cotas,
                        "plan": action.get("plan"),
                        "source": provenance(action.get("source")),
                        "scope": "proposal_not_execution",
                    },
                )
            )
    return documents


def in_scope(
    passage: Passage,
    *,
    part: str | None = None,
    feature_id: str | None = None,
    revision: str | None = None,
    characteristic: str | None = None,
) -> bool:
    data = passage.scope
    if part and part not in data.get("parts", []):
        return False
    if feature_id and data.get("feature_id") != feature_id:
        return False
    if data.get("scope") == "feature_general":
        return not (revision or characteristic) or any(
            (not part or link["part"] == part)
            and (not revision or link["revision"] == revision)
            and (not characteristic or link["characteristic"] == characteristic)
            for link in data.get("links", [])
        )
    return (not revision or data.get("revision") == revision) and (
        not characteristic or characteristic in data.get("characteristics", [])
    )
