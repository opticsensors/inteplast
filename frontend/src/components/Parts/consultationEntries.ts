import type { CharacteristicPublic, MetrologyFeature } from "@/client"
import type { PartSearch } from "./measurementSelection"
import type { Entry, Study } from "./types"

export const hasFeatureFilters = (search: PartSearch) =>
  Boolean(search.feature || search.category || search.tag)

export const matchesFeatureFilters = (
  feature: Pick<MetrologyFeature, "id" | "name" | "category" | "tags">,
  search: PartSearch,
) =>
  (!search.feature || feature.id === search.feature) &&
  (!search.category || feature.category === search.category) &&
  (!search.tag || feature.tags?.includes(search.tag))

/** Category and tag must match the same feature, then use only its real cota links. */
export function consultationScope(
  features: MetrologyFeature[],
  search: PartSearch,
): MetrologyFeature | null | undefined {
  if (!hasFeatureFilters(search)) return undefined
  if (
    search.feature &&
    !features.some((feature) => feature.id === search.feature)
  )
    return null
  const matching = features.filter((feature) =>
    matchesFeatureFilters(feature, search),
  )
  return {
    id: "selection",
    name: "Selección",
    characteristics: matching.flatMap(
      (feature) => feature.characteristics ?? [],
    ),
  }
}

const withoutMeasurements = (cota: CharacteristicPublic): Entry => ({
  id: cota.code,
  numbers: [cota.code],
  title: cota.title,
  revision: cota.revision,
  kind: "dimension",
  series: [],
  actions: [],
  reviewed_case: null,
})

/** A scope uses actual assignments, including cotas with no imported measurements. */
export function consultationEntries(
  study: Study | undefined,
  characteristics: CharacteristicPublic[],
  feature: MetrologyFeature | null | undefined,
): Entry[] {
  const measured = (study?.catalog.entries ?? []).filter(
    (entry) => entry.kind !== "diagnostic",
  )
  if (feature !== undefined) {
    const byCode = new Map<string, Entry>()
    for (const cota of feature?.characteristics ?? []) {
      const match =
        cota.revision === study?.measurement_revision
          ? measured.find(
              (entry) =>
                entry.numbers.includes(cota.code) || entry.id === cota.code,
            )
          : undefined
      if (!byCode.has(cota.code) || match)
        byCode.set(
          cota.code,
          match
            ? {
                ...match,
                id: cota.code,
                numbers: [cota.code],
                revision: cota.revision,
              }
            : withoutMeasurements(cota),
        )
    }
    return [...byCode.values()]
  }
  const entries: Entry[] = measured.map((entry) => ({
    ...entry,
    revision: study?.measurement_revision,
  }))
  for (const cota of characteristics) {
    if (
      !entries.some(
        (entry) => entry.id === cota.code || entry.numbers.includes(cota.code),
      )
    )
      entries.push(withoutMeasurements(cota))
  }
  return entries.sort((a, b) =>
    a.id.localeCompare(b.id, "es", { numeric: true }),
  )
}
