"""Whether the app has read measurements of a piece, for its catalogue label.

- "detected": at least one valid value, with its cota number and its source file and
  cell, even while the rest of the read is still running.
- "pending": the read finished without values, but a measurement report was found that
  the reader could not interpret (rows without cota numbers, unlabelled columns…).
- "none": the read finished and there were no measurement reports at all.
- None: the piece has not been read yet, or its read is still running or failed.

Only what the app read from the originals counts; nothing is inferred from file names.
"""

import uuid
from typing import Literal

from sqlalchemy import text
from sqlmodel import Session

from app.models import Part

MeasurementStatus = Literal["detected", "pending", "none"]

# Only the import in force of each revision, sample and cavity counts: the latest by
# `imported_at`, then `id`, as in the measurement history (`history_summary`). A newer
# empty import retires the values that are no longer in the original; a baseline in
# force leaves that combination without an active import.
# Within it, the rule of `usable_measurement`, plus a numeric value, a cota number and
# a source with file and cell. EXISTS stops at the first valid row of the piece.
VALID_VALUE = text(
    """
    with in_force as (
      select distinct on (revision, sample, cavity) baseline, rows
      from measurementimport
      where part_id = :part
      order by revision, sample, cavity, imported_at desc, id desc
    )
    select exists (
      select 1
      from in_force m, json_array_elements(m.rows) r
      where (m.baseline is null or m.baseline::text = 'null')
        and coalesce(r->>'provenance_state', 'medicion') = 'medicion'
        and not coalesce(
          (coalesce(r->'flags', r->'exclusion_reasons', '[]'::json))::jsonb ? 'copia',
          false
        )
        and json_typeof(r->'value') = 'number'
        and json_typeof(r->'numbers') = 'array'
        and json_array_length(r->'numbers') > 0
        and coalesce(r->'source'->>'path', '') <> ''
        and coalesce(r->'source'->>'locator', '') <> ''
    )
    """
)


def has_valid_measurement(session: Session, part_id: uuid.UUID) -> bool:
    return bool(session.execute(VALID_VALUE, {"part": part_id}).scalar())


def measurement_status(session: Session, part: Part) -> MeasurementStatus | None:
    if has_valid_measurement(session, part.id):
        return "detected"
    # The live state: a stored "processing" ends when the correction study ends.
    from app.part_reading import read_report

    report = read_report(session, part)
    if report is None or report.state not in {"ready", "partial"}:
        return None
    if any(item.group == "measurements" for item in report.files):
        return "pending"
    return "none"


def corrections_documented(session: Session, part: Part) -> bool | None:
    """Only a completed read can establish that correction documents are absent."""
    from app.part_reading import read_report

    report = read_report(session, part)
    if report is None or "corrections_state" not in report.model_fields_set:
        return None
    if report.corrections_state != "empty":
        return True
    return False if report.state in {"ready", "partial"} else None
