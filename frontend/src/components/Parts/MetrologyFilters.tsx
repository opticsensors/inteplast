import type { MetrologyFilters as Options, PartPublic } from "@/client"
import { SearchSelect } from "@/components/Common/SearchSelect"
import { partLabel } from "@/components/Features/parts"
import type { PartSearch } from "./measurementSelection"

/** Pieza y Feature. Categoría y Tag se retiraron el 17/11/2026. */
export function MetrologyFilters({
  options,
  partId,
  part,
  search,
  onPart,
  onScope,
  hidePart = false,
}: {
  options?: Options
  partId?: string
  part?: PartPublic
  search: PartSearch
  onPart: (id: string | undefined) => void
  onScope: (values: Partial<PartSearch>) => void
  hidePart?: boolean
}) {
  const allFeatures = options?.features ?? []
  const availableFeatures = allFeatures.filter(
    (feature) => !partId || feature.part_ids?.includes(partId),
  )
  const parts = (options?.parts ?? []).filter(
    (piece) =>
      !search.feature ||
      allFeatures.some(
        (feature) =>
          feature.id === search.feature && feature.part_ids?.includes(piece.id),
      ),
  )
  return (
    <div className={hidePart ? "grid gap-2" : "grid gap-2 sm:grid-cols-2"}>
      {!hidePart && (
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
      )}
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
    </div>
  )
}
