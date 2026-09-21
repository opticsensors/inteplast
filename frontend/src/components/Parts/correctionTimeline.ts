import { correctionFor, type Evaluation } from "./measurementSelection"
import type { Action, Entry, Study } from "./types"

export type CorrectionInterval = {
  id: string
  before: string
  after: string
  from: number
  to: number
  plans: { id: string; date: string }[]
  actions: Action[]
  description?: string
  comparison?: ReturnType<typeof correctionFor>
}

/** Existing source associations provide the actions; measurements alone never imply a retouch. */
export function correctionTimeline(
  study: Study,
  entry: Entry,
  evaluation: Evaluation,
) {
  const definition = entry.reviewed_case
    ? study.cases[entry.reviewed_case]
    : undefined
  const comparison = correctionFor(study, entry, evaluation)
  // The reviewed slides already exclude their corporate logo. Exclude those same
  // image IDs when presenting other slides from the complete action index.
  const decorativeImages = new Set(
    Object.entries(study.actions).flatMap(([id, detail]) =>
      (study.action_index[id]?.images ?? [])
        .filter(
          (image) => !detail.images.some((kept) => kept.url === image.url),
        )
        .map((image) => image.url),
    ),
  )
  const actions = [
    ...new Set([...entry.actions, ...(definition?.actions ?? [])]),
  ].flatMap((id) => {
    const indexed = study.action_index[id]
    const detail = study.actions[id]
    return indexed || detail
      ? [
          {
            ...indexed,
            ...detail,
            plan: indexed?.plan ?? detail?.plan ?? id.split(".")[0],
            images: (detail?.images ?? indexed?.images ?? []).filter(
              (image) => !decorativeImages.has(image.url),
            ),
          } as Action,
        ]
      : []
  })
  return study.samples.slice(1).map((after, index): CorrectionInterval => {
    const before = study.samples[index]
    const plans = Object.entries(study.corrections)
      .filter(([, plan]) => plan.before === before && plan.after === after)
      .map(([id, plan]) => ({ id, date: plan.date }))
    const mapped =
      comparison &&
      plans.some((plan) => plan.id === comparison.definition.correction)
        ? comparison
        : undefined
    return {
      id: `${before}-${after}`,
      before,
      after,
      from: index,
      to: index + 1,
      plans,
      actions: actions.filter((action) =>
        plans.some((plan) => plan.id === action.plan),
      ),
      description: mapped?.definition.description,
      comparison: mapped,
    }
  })
}

export function intervalValues(
  interval: CorrectionInterval,
  evaluation: Evaluation,
  cavity: string,
) {
  const records = evaluation.series.records[cavity]
  const before = records?.[interval.before]
  const after = records?.[interval.after]
  const comparison =
    interval.comparison?.comparisons[cavity]?.items[interval.comparison.index]
  const numeric = (value: number | null | undefined): value is number =>
    value != null && Number.isFinite(value)
  return {
    before,
    after,
    comparison,
    measuredChange:
      numeric(before?.value) && numeric(after?.value)
        ? after.value - before.value
        : null,
    // Use the saved XLS baseline, which may differ from the CSV measurement.
    expectedChange:
      numeric(comparison?.prediction) && numeric(comparison?.xls_before)
        ? comparison.prediction - comparison.xls_before
        : null,
  }
}

export function proposalParagraphs(action: Action) {
  return action.paragraphs.filter(
    (text) =>
      text.trim() &&
      !/^(Tool correction|Longitud|Current situation|\d+\s*\/\s*\d+$|OK$)/i.test(
        text.trim(),
      ),
  )
}
