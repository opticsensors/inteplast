"""Provider-independent evidence for imported correction plans.

Never infer dimensions from document headings or execution from a plan. Numeric
limits come exclusively from the structured measurement records. Unknown document
layouts retain their original text instead of guessing which sentence is a proposal.
"""

import math
import re
from typing import Any

from app.assistant.retrieval import normalize

PROPOSAL_HEADINGS = {
    "tool correction plan",
    "correction plan",
    "proposed correction",
    "plan de correccion",
    "plan de retoque",
    "propuesta de correccion",
    "pla de correccio",
    "proposta de correccio",
}
OTHER_HEADINGS = {
    "current situation",
    "situacion actual",
    "situacio actual",
    "results",
    "resultados",
    "resultats",
    "verification",
    "verificacion",
    "verificacio",
    "notes",
    "notas",
    "observaciones",
    "observacions",
}


def proposal_blocks(paragraphs: list[str]) -> list[str]:
    """Extract only explicitly headed blocks; no inference from engineering terms."""
    blocks: list[str] = []
    current: list[str] | None = None
    for paragraph in paragraphs:
        # A heading may have its body on the same line after a colon.
        heading, separator, body = paragraph.partition(":")
        label = normalize(heading if separator else paragraph)
        if label in PROPOSAL_HEADINGS:
            if current:
                blocks.append("\n".join(current))
            current = [body.strip()] if body.strip() else []
        elif label in OTHER_HEADINGS:
            if current:
                blocks.append("\n".join(current))
            current = None
        elif current is not None:
            current.append(paragraph)
    if current:
        blocks.append("\n".join(current))
    return blocks


def plan_evidence(action: dict[str, Any]) -> dict[str, Any]:
    from app.assistant.tools import clipped, provenance

    paragraphs = [
        p for p in action.get("paragraphs", []) if isinstance(p, str) and p.strip()
    ]
    original = "\n".join(paragraphs)
    proposals = proposal_blocks(paragraphs)
    return {
        # Retain id for tool clients, and expose the domain identifier separately
        # so the general UUID privacy filter cannot erase an action reference.
        "id": action.get("id"),
        "action_id": action.get("id"),
        "plan": action.get("plan"),
        "title": action.get("title"),
        "features": action.get("features", []),
        "link_method": action.get("link_method"),
        "evidence_kind": "correction_plan",
        "title_role": "document_heading",
        "proposal_status": "explicit_heading" if proposals else "not_separated",
        "proposal_quote": clipped("\n\n".join(proposals), 1400) if proposals else None,
        "text": clipped(original, 1800),
        "text_truncated": len(original) > 1800 or len("\n\n".join(proposals)) > 1400,
        "execution_status": "not_established_by_this_plan",
        "source": provenance(action.get("source")),
    }


def finite_number(value: Any) -> float | int | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    ):
        return value
    return None


def recorded_limits(
    entries: list[dict[str, Any]], *, cavity: str | None, sample: str | None
) -> list[dict[str, Any]]:
    """Keep different characteristics, units and tolerance regimes separate.

    Series sharing identical limits can share one row. Their names, cavities,
    samples and source documents remain attached; no nominal or unit is inferred.
    """
    from app.assistant.tools import provenance

    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for entry in entries:
        for series in entry.get("series", []):
            for cav, samples in series.get("records", {}).items():
                for sampling, record in samples.items():
                    if (cavity and cav != cavity) or (sample and sampling != sample):
                        continue
                    nominal, lower, upper = (
                        finite_number(record.get(k))
                        for k in ("nominal", "lower", "upper")
                    )
                    if nominal is None and lower is None and upper is None:
                        continue
                    key = (entry["id"], series.get("unit"), nominal, lower, upper)
                    group = groups.setdefault(
                        key,
                        {
                            "characteristic": entry["id"],
                            "unit": series.get("unit"),
                            "nominal": nominal,
                            "lower": lower,
                            "upper": upper,
                            "series": set(),
                            "cavities": set(),
                            "samples": set(),
                            "documents": set(),
                        },
                    )
                    group["series"].add(
                        series.get("label") or series.get("id") or "sin identificar"
                    )
                    group["cavities"].add(cav)
                    group["samples"].add(sampling)
                    source = provenance(record.get("source"))
                    if source.get("document"):
                        group["documents"].add(source["document"])
    return [
        {k: sorted(v) if isinstance(v, set) else v for k, v in g.items()}
        for g in groups.values()
    ]


def direct_question(question: str) -> bool:
    """Conservative intent gate, independent of entity IDs and provider/model.

    This renderer uses the application's Spanish labels. Explanations, other
    languages and questions about execution retain the normal model/tool route.
    """
    text = normalize(question)
    return bool(re.search(r"\b(?:corre?c+ion\w*|retoqu\w*)\b", text)) and not bool(
        re.search(
            r"explic|interpre|compar|por que|causa|evoluc|relaci|efecto|impacto|recom|signific|justifi|"
            r"ejecut|aplic|realiz|resuelt|resolvi|cumpl|conform|funcion|mejor|peor|"
            r"medici|medida|valor|toleran|advertenc|lecci|notas|tradu|ingles|english|frances|catalan",
            text,
        )
    )
