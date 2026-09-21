import { matchesCotaPrefix } from "@/components/Features/drawingSearchHelpers"
import type { Entry, Series, Study } from "./types"

export type PartSearch = {
  q?: string
  cota?: string
  element?: string
  height?: string
  evaluation?: string
  cavities?: string
  interval?: string
  action?: string
  cavity?: string
  view?: "correcciones"
  plano?: true
  drawingQ?: string
}
const text = (value: unknown) =>
  typeof value === "string" || typeof value === "number"
    ? String(value) || undefined
    : undefined

export function validatePartSearch(
  search: Record<string, unknown>,
): PartSearch {
  return {
    q: typeof search.q === "string" ? search.q : text(search.q),
    cota: text(search.cota) ?? text(search.caso),
    element: text(search.element),
    height: text(search.height),
    evaluation: text(search.evaluation),
    cavities: text(search.cavities),
    interval: text(search.interval),
    action: text(search.action),
    cavity: text(search.cavity),
    plano: search.plano === true || search.plano === "true" ? true : undefined,
    drawingQ: typeof search.drawingQ === "string" ? search.drawingQ : undefined,
    view:
      search.view === "correcciones" || search.tab === "correcciones"
        ? "correcciones"
        : undefined,
  }
}

export type Evaluation = {
  series: Series
  element: string
  height: string
  metric: string
  label: string
  variant?: string
  comparisonIndex?: number
}

/** The N170 identity is derived from CMM IDs by the importer, never its repeated header. */
export function describeSeries(entry: Entry, series: Series): Evaluation {
  const bolt = /^N170\|(B[1-4])-H(1\.5|5\.0)\|([12])$/.exec(series.id)
  if (bolt)
    return {
      series,
      element: bolt[1],
      height: bolt[2],
      metric: bolt[3],
      label: bolt[3] === "1" ? "GX" : "LP máximo",
      variant: `${bolt[1]}-H${bolt[2]}`,
      comparisonIndex: Number(bolt[3]) - 1,
    }
  const [identityBlock, occurrence = "1", identityIndex = "1"] =
    series.id.split("|")
  const block = series.block ?? identityBlock
  const idx = series.idx ?? Number(identityIndex)
  const suffix = occurrence === "1" ? "" : ` · aparición ${occurrence}`
  const point = /^POINT\s+(\d+)/.exec(block)
  const otherBolt = /\bBOLT\s+([1-4])\b/.exec(block)
  let element = point
    ? `P${point[1].padStart(2, "0")}`
    : otherBolt
      ? `B${otherBolt[1]}`
      : block
  let label = series.label.replace(/^.* · \[\d+\]\s*/, "")
  let variant: string | undefined
  let comparisonIndex: number | undefined
  if (
    entry.id === "N161" &&
    block.startsWith("N161 ") &&
    [1, 2].includes(idx)
  ) {
    element = "Diámetro"
    label = idx === 1 ? "GX" : "LP(2) máximo"
    if (occurrence === "1") {
      variant = "main"
      comparisonIndex = idx - 1
    }
  } else if (entry.id === "N240" && block.startsWith("N240 ") && idx === 1) {
    element = "Distancia"
    label = "Distancia"
    if (occurrence === "1") {
      variant = "main"
      comparisonIndex = 0
    }
  } else if (entry.id === "N165") {
    const global = block.startsWith("GLOBAL ")
    element = global
      ? "GLOBAL"
      : block.startsWith("N165 MIN")
        ? "Escaneo"
        : element
    label = idx === 1 ? "Mínimo" : idx === 2 ? "Máximo" : label
    if (global && occurrence === "1" && [1, 2].includes(idx)) {
      variant = "main"
      comparisonIndex = idx - 1
    }
  }
  return {
    series,
    element: element + suffix,
    height: "",
    metric: String(idx),
    label,
    variant,
    comparisonIndex,
  }
}

export function selectEvaluation(entry: Entry, search: PartSearch) {
  const all = entry.series.map((series) => describeSeries(entry, series))
  const elements = [...new Set(all.map((item) => item.element))]
  const element = elements.includes(search.element ?? "")
    ? search.element!
    : elements[0]
  const byElement = all.filter((item) => item.element === element)
  const heights = [...new Set(byElement.map((item) => item.height))]
  const height = heights.includes(search.height ?? "")
    ? (search.height ?? "")
    : heights[0]
  const evaluations = byElement.filter((item) => item.height === height)
  const selected =
    evaluations.find((item) => item.metric === search.evaluation) ??
    evaluations[0]
  return { elements, heights, evaluations, selected }
}

export function correctionFor(
  study: Study,
  entry: Entry,
  selected?: Evaluation,
) {
  const code = entry.reviewed_case
  const definition = code ? study.cases[code] : undefined
  if (!definition || !selected?.variant || selected.comparisonIndex == null)
    return undefined
  const comparisons = definition.comparisons[selected.variant]
  const plan = study.corrections[definition.correction]
  if (!comparisons || !plan) return undefined
  return { definition, comparisons, plan, index: selected.comparisonIndex }
}

export function visibleCavities(cavities: string[], search?: string) {
  const selected = search
    ?.split(",")
    .filter((value) => cavities.includes(value))
  return selected?.length ? selected : cavities
}

export function findEntries(entries: Entry[], query: string) {
  const needle = query.trim().toUpperCase()
  const number = /^N?\s*0*(\d+(?:\.\d+)?)$/.exec(needle)
  return entries
    .filter((entry) =>
      number
        ? entry.numbers.some((code) => matchesCotaPrefix(code, needle))
        : `${entry.id} ${entry.title}`.toUpperCase().includes(needle),
    )
    .sort((a, b) =>
      number
        ? Number(b.numbers.includes(`N${number[1]}`)) -
          Number(a.numbers.includes(`N${number[1]}`))
        : 0,
    )
}
