"""Exact measurement facts without asking a small LLM to reinterpret numbers."""

import re
from typing import Any


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
