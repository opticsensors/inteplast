"""Exact measurement facts without asking a small LLM to reinterpret numbers."""

import re
from html import escape
from typing import Any

from app.assistant.corrections import direct_question


def literal(value: Any) -> str:
    """Render source text as text, not as active Markdown/HTML instructions."""
    return re.sub(r"([\\`*_{}\[\]#|])", r"\\\1", escape(str(value), quote=False))


def correction_answer(question: str, result: dict[str, Any]) -> str | None:
    """Factual plan lookups with exact quotes, for any model, piece or action."""
    if not direct_question(question) or "actions" not in result or result.get("error"):
        return None
    coverage = result.get("coverage", {})
    if not coverage.get("actions", {}).get("complete"):
        return None
    actions = result["actions"]
    if any(a.get("text_truncated") for a in actions):
        return None
    scope = f"Pieza **{literal(result['name'] or result['part'])} ({literal(result['part'])})**"
    if result.get("feature"):
        scope += f", feature **{literal(result['feature'])}**"
    if result.get("filters", {}).get("characteristic"):
        scope += f", cota **{literal(result['filters']['characteristic'])}**"
    if result.get("revision"):
        scope += f", revisión **{literal(result['revision'])}**"
    lines = [scope + ".", ""]
    if not actions:
        lines.append(
            "No se han recuperado planes de corrección importados para este ámbito. Esto no demuestra que no existan retoques en otras fuentes."
        )
    for action in actions:
        reference = action.get("action_id") or action.get("id")
        lines.append(
            f"**Corrección {literal(reference)}**"
            if reference
            else "**Plan de corrección**"
        )
        if action.get("title"):
            lines.append("Referencia en el documento: " + literal(action["title"]))
        quote = action.get("proposal_quote") or action.get("text")
        if quote:
            lines.extend(
                [
                    "",
                    "Propuesta (texto original):"
                    if action.get("proposal_quote")
                    else "Texto original del documento (sin separar una propuesta):",
                    "",
                ]
            )
            lines.extend("> " + literal(line) for line in quote.splitlines())
        else:
            lines.append("No hay texto importado que detalle la propuesta.")
        source = action.get("source", {})
        source_label = " · ".join(
            literal(source[k])
            for k in ("document", "locator", "sheet", "row")
            if source.get(k)
        )
        lines.extend(
            [
                "",
                "Fuente: " + source_label
                if source_label
                else "Fuente documental sin localizador importado.",
                "",
            ]
        )
    # Limits are supporting context for this intent, not part of the requested
    # plan inventory. Omit incomplete optional context rather than rewriting a
    # complete plan with an LLM or suggesting that the partial limits are all.
    limits = (
        result.get("recorded_limits", [])
        if coverage.get("recorded_limits", {}).get("complete")
        else []
    )
    if limits:
        lines.extend(["Límites de las cotas según las mediciones importadas:", ""])
        for limit in limits:
            unit = literal(limit.get("unit") or "(unidad no indicada)")
            lower, upper = limit.get("lower"), limit.get("upper")
            fields = []
            if limit.get("nominal") is not None:
                fields.append(f"nominal {number(limit['nominal'])} {unit}")
            if lower is not None and upper is not None:
                if lower <= upper:
                    fields.append(f"límites {number(lower)}–{number(upper)} {unit}")
                else:
                    fields.append(
                        f"límites inconsistentes en origen: inferior {number(lower)}, superior {number(upper)} {unit}"
                    )
            elif lower is not None:
                fields.append(
                    f"límite inferior {number(lower)} {unit}; superior no indicado"
                )
            elif upper is not None:
                fields.append(
                    f"límite superior {number(upper)} {unit}; inferior no indicado"
                )
            # Different regimes must retain their series and sampling context.
            same_cota = sum(
                item["characteristic"] == limit["characteristic"] for item in limits
            )
            detail = ""
            if same_cota > 1:
                detail = (
                    " ("
                    + "; ".join(
                        literal(", ".join(limit.get(k, [])))
                        for k in ("series", "cavities", "samples")
                        if limit.get(k)
                    )
                    + ")"
                )
            lines.append(
                f"- **{literal(limit['characteristic'])}**{detail}: "
                + "; ".join(fields)
                + "."
            )
        lines.extend(
            [
                "",
                "Estos valores describen las cotas registradas en las mediciones; no especifican las dimensiones de una herramienta.",
            ]
        )
    lines.extend(
        [
            "",
            "El plan por sí solo no acredita la ejecución del retoque ni la conformidad final de la pieza.",
        ]
    )
    return "\n".join(lines)


def number(value: Any) -> str:
    return "—" if value is None else str(value).replace(".", ",")


def measurement_answer(question: str, result: dict[str, Any]) -> str | None:
    # Explanations/comparisons and other languages retain the model/tool path.
    if not re.search(
        r"\b(mediciones|medidas|tolerancias|muestreos|cavidades|registros|promedio|mínimo|máximo|valores)\b",
        question,
        re.I,
    ):
        return None
    if re.search(
        r"explica|interpreta|recomien|significa|causa|compar|evoluci|por qu[eé]|mejor|relaci",
        question,
        re.I,
    ):
        return None
    summary = result.get("summary")
    if not summary or not summary.get("total") or result.get("rows"):
        return None
    scope = f"Pieza **{result['part']}**, revisión **{result.get('revision') or 'sin indicar'}**"
    filters = result.get("filters", {})
    if filters.get("characteristic"):
        scope += f", cota **{filters['characteristic']}**"
    lines = [
        scope + ".",
        "",
        f"**{summary['total']} mediciones** en {summary['series_total']} series.",
        f"- Cavidades: {', '.join(summary['cavities'])}.",
        f"- Muestreos: {', '.join(summary['samples'])}.",
    ]
    for tolerance in summary["tolerances"]:
        lower, upper, unit = (
            tolerance["lower"],
            tolerance["upper"],
            tolerance["unit"] or "",
        )
        if lower is not None and upper is not None:
            bounds = f"{number(lower)}–{number(upper)} {unit}"
        elif upper is not None:
            bounds = f"máximo {number(upper)} {unit}"
        elif lower is not None:
            bounds = f"mínimo {number(lower)} {unit}"
        else:
            bounds = "sin límites registrados"
        lines.append(f"- Límites registrados: **{bounds.strip()}**.")
    counts = summary["status_counts"]
    if "inside" in counts or "outside" in counts:
        lines.append(
            f"- Resultado: **{counts.get('inside', 0)} dentro** y **{counts.get('outside', 0)} fuera** de los límites."
        )
    other = sum(
        count for status, count in counts.items() if status not in {"inside", "outside"}
    )
    if other:
        lines.append(f"- Otras mediciones sin clasificación dentro/fuera: {other}.")
    if result.get("series_summaries"):
        lines.extend(["", "Estadísticas por serie:"])
        for values in result["series_summaries"]:
            row = dict(zip(result["series_columns"], values, strict=True))
            lines.append(
                f"- {row['characteristic']} · {row['series']} ({row['unit']}): mínimo {number(row['min'])}, máximo {number(row['max'])}, media {number(row['mean'])}; {row['count']} mediciones."
            )
    if summary["documents"]:
        lines.extend(["", "Fuentes: " + ", ".join(summary["documents"]) + "."])
    return "\n".join(lines)
