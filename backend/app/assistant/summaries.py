"""Exact aggregates over all filtered records, independent of the example page."""

import math
from collections import Counter
from typing import Any


def page(total: int, offset: int, returned: int) -> dict[str, Any]:
    return {
        "total": total,
        "offset": offset,
        "returned": returned,
        "complete": offset == 0 and returned == total,
        "next_offset": offset + returned if offset + returned < total else None,
    }


def measurements(
    entries: list[dict[str, Any]],
    *,
    cavity: str | None,
    sample: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    from app.assistant.tools import provenance

    rows: list[dict[str, Any]] = []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for entry in entries:
        for series in entry.get("series", []):
            for cav, samples in series.get("records", {}).items():
                for sampling, record in samples.items():
                    if (cavity and cavity != cav) or (sample and sample != sampling):
                        continue
                    row = {
                        "characteristic": entry["id"],
                        "series_id": series.get("id"),
                        "series": series.get("label"),
                        "unit": series.get("unit"),
                        "cavity": cav,
                        "sample": sampling,
                        **{
                            k: record.get(k)
                            for k in (
                                "value",
                                "nominal",
                                "lower",
                                "upper",
                                "deviation",
                                "status",
                            )
                        },
                        "source": provenance(record.get("source")),
                    }
                    rows.append(row)
                    # Never aggregate different series, units or tolerance regimes.
                    key = (
                        entry["id"],
                        series.get("id") or series.get("label"),
                        series.get("unit"),
                        record.get("nominal"),
                        record.get("lower"),
                        record.get("upper"),
                    )
                    groups.setdefault(key, []).append(row)

    aggregates = []
    for group in groups.values():
        first = group[0]
        values = [
            r["value"]
            for r in group
            if isinstance(r["value"], (int, float))
            and not isinstance(r["value"], bool)
            and math.isfinite(r["value"])
        ]
        aggregates.append(
            {
                **{
                    k: first[k]
                    for k in (
                        "characteristic",
                        "series_id",
                        "series",
                        "unit",
                        "nominal",
                        "lower",
                        "upper",
                    )
                },
                "count": len(group),
                "numeric_count": len(values),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "mean": round(math.fsum(values) / len(values), 10) if values else None,
                "status_counts": dict(Counter(r["status"] or "unknown" for r in group)),
            }
        )
    summary = {
        "scope": "all_filtered_records",
        "total": len(rows),
        "cavities": sorted({r["cavity"] for r in rows}),
        "samples": sorted({r["sample"] for r in rows}),
        "status_counts": dict(Counter(r["status"] or "unknown" for r in rows)),
        "series_total": len(
            {
                (g["characteristic"], g["series_id"] or g["series"], g["unit"])
                for g in aggregates
            }
        ),
        "statistical_groups_total": len(aggregates),
        "tolerances": [
            dict(zip(("unit", "nominal", "lower", "upper"), limit, strict=True))
            for limit in dict.fromkeys(
                (g["unit"], g["nominal"], g["lower"], g["upper"]) for g in aggregates
            )
        ],
        "documents": sorted(
            {r["source"]["document"] for r in rows if r["source"].get("document")}
        ),
    }
    return summary, aggregates, rows
