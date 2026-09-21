import { SlidersHorizontal } from "lucide-react"
import { useState } from "react"
import type {
  FeatureCategory,
  MetrologyFilters as Options,
  PartPublic,
} from "@/client"
import { SearchSelect } from "@/components/Common/SearchSelect"
import { CATEGORY_LABELS } from "@/components/Features/constants"
import { partLabel } from "@/components/Features/parts"
import { Button } from "@/components/ui/button"
import { matchesFeatureFilters } from "./consultationEntries"
import type { PartSearch } from "./measurementSelection"

export function MetrologyFilters({
  options,
  partId,
  part,
  search,
  onPart,
  onScope,
}: {
  options?: Options
  partId?: string
  part?: PartPublic
  search: PartSearch
  onPart: (id: string | undefined) => void
  onScope: (values: Partial<PartSearch>) => void
}) {
  const [more, setMore] = useState(Boolean(search.category || search.tag))
  const allFeatures = options?.features ?? []
  const inPiece = allFeatures.filter(
    (feature) => !partId || feature.part_ids?.includes(partId),
  )
  const parts = (options?.parts ?? []).filter((piece) =>
    allFeatures.some(
      (feature) =>
        feature.part_ids?.includes(piece.id) &&
        matchesFeatureFilters(feature, search),
    ),
  )
  const availableFeatures = inPiece.filter((feature) =>
    matchesFeatureFilters(feature, { ...search, feature: undefined }),
  )
  const categories = [
    ...new Set(
      inPiece
        .filter((feature) =>
          matchesFeatureFilters(feature, { ...search, category: undefined }),
        )
        .flatMap((feature) => (feature.category ? [feature.category] : [])),
    ),
  ]
  const tags = [
    ...new Set(
      inPiece
        .filter((feature) =>
          matchesFeatureFilters(feature, { ...search, tag: undefined }),
        )
        .flatMap((feature) => feature.tags ?? []),
    ),
  ].sort()
  const changeScope = (values: Partial<PartSearch>) => {
    const next = { ...search, ...values }
    const current = allFeatures.find((feature) => feature.id === next.feature)
    onScope({
      ...values,
      feature:
        current && matchesFeatureFilters(current, next)
          ? current.id
          : undefined,
    })
  }
  const active = Number(Boolean(search.category)) + Number(Boolean(search.tag))
  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
        <SearchSelect
          label="Pieza"
          value={partId}
          placeholder="Seleccionar pieza"
          emptyLabel="Seleccionar pieza"
          selectedLabel={part ? partLabel(part) : undefined}
          options={parts.map((part) => ({
            value: part.id,
            label: partLabel(part),
          }))}
          onChange={onPart}
          disabled={!options}
        />
        <SearchSelect
          label="Feature"
          selectedLabel={
            allFeatures.find((feature) => feature.id === search.feature)?.name
          }
          value={search.feature}
          placeholder="Todos los features"
          emptyLabel="Todos los features"
          options={availableFeatures.map((feature) => ({
            value: feature.id,
            label: feature.name,
          }))}
          onChange={(feature) => onScope({ feature })}
          disabled={!options}
        />
        <Button
          type="button"
          variant="outline"
          className="h-9 font-normal"
          aria-expanded={more}
          onClick={() => setMore(!more)}
        >
          <SlidersHorizontal className="size-4" /> Más filtros
          {active ? ` (${active})` : ""}
        </Button>
      </div>
      {more && (
        <div className="grid gap-2 sm:grid-cols-2">
          <SearchSelect
            label="Categoría"
            selectedLabel={
              search.category ? CATEGORY_LABELS[search.category] : undefined
            }
            value={search.category}
            placeholder="Todas las categorías"
            emptyLabel="Todas las categorías"
            options={categories.map((category) => ({
              value: category,
              label: CATEGORY_LABELS[category],
            }))}
            onChange={(category) =>
              changeScope({ category: category as FeatureCategory | undefined })
            }
            disabled={!options}
          />
          <SearchSelect
            label="Tag"
            selectedLabel={search.tag}
            value={search.tag}
            placeholder="Todos los tags"
            emptyLabel="Todos los tags"
            options={tags.map((tag) => ({ value: tag, label: tag }))}
            onChange={(tag) => changeScope({ tag })}
            disabled={!options}
          />
        </div>
      )}
    </div>
  )
}
