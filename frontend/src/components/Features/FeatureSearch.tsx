import { useQuery } from "@tanstack/react-query"
import { SlidersHorizontal, X } from "lucide-react"
import { useId, useState } from "react"

import { EvidenceService, type FeatureCategory } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { SearchSelect } from "@/components/Common/SearchSelect"
import { SearchToolbar } from "@/components/Common/SearchToolbar"
import { Button } from "@/components/ui/button"
import { CATEGORIES, CATEGORY_LABELS } from "./constants"
import { partLabel } from "./parts"
import { featureFiltersQueryOptions } from "./queries"

export interface FeatureSearchState {
  q: string
  category: FeatureCategory | null
  tag: string | null
  partId: string | null
  featureId: string | null
}

export const EMPTY_SEARCH: FeatureSearchState = {
  q: "",
  category: null,
  tag: null,
  partId: null,
  featureId: null,
}

/**
 * La busqueda tambien vive en la URL (`/features?q=bolt&part=<id>`). Asi el boton de
 * atras del navegador devuelve los resultados al volver de la ficha, y una
 * busqueda se puede compartir o guardar en favoritos.
 */
export interface FeatureSearchParams {
  kind?: "all" | "part" | "feature"
  q?: string
  category?: FeatureCategory
  tag?: string
  part?: string
  feature?: string
}

/**
 * Nadie garantiza lo que llega en la URL: lo que no cuadre, fuera.
 *
 * 🔴 El router pasa cada valor por `JSON.parse`, asi que `?q=3212` llega aqui
 * como el **numero** 3212 — y buscar codigos de pieza es justo el caso normal.
 * Por eso se convierte a texto en vez de exigir `typeof === "string"`.
 */
export const validateFeatureSearch = (
  search: Record<string, unknown>,
): FeatureSearchParams => {
  const text = (value: unknown) =>
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
      ? String(value) || undefined
      : undefined
  const category = text(search.category)

  return {
    kind:
      search.kind === "part" || search.kind === "feature"
        ? search.kind
        : undefined,
    q: text(search.q),
    category: CATEGORIES.includes(category as FeatureCategory)
      ? (category as FeatureCategory)
      : undefined,
    tag: text(search.tag),
    part: text(search.part),
    feature: text(search.feature),
  }
}

export const toSearchState = (
  params: FeatureSearchParams,
): FeatureSearchState => ({
  q: params.q ?? "",
  category: params.category ?? null,
  tag: params.tag ?? null,
  partId: params.part ?? null,
  featureId: params.feature ?? null,
})

/** Los vacios se omiten para no arrastrar un `?q=&tag=` por toda la app. */
export const toSearchParams = (
  state: FeatureSearchState,
): FeatureSearchParams => ({
  q: state.q || undefined,
  category: state.category ?? undefined,
  tag: state.tag ?? undefined,
  part: state.partId ?? undefined,
  feature: state.featureId ?? undefined,
})

interface FeatureSearchProps {
  value: FeatureSearchState
  onChange: (value: FeatureSearchState) => void
  catalog?: boolean
}

/** Buscador global + filtros por pieza, feature, categoria y tag. */
export function FeatureSearch({
  value,
  onChange,
  catalog = false,
}: FeatureSearchProps) {
  const [filtersOpen, setFiltersOpen] = useState(false)
  const filtersId = useId()
  // Solo se ofrecen los valores que existen en la base de datos
  const { data: featureFilters } = useQuery(featureFiltersQueryOptions())
  const all = useQuery({
    queryKey: ["metrology-filters"],
    queryFn: () => EvidenceService.readMetrologyFilters(),
    enabled: catalog,
  })
  const filters =
    catalog && all.data ? { ...featureFilters, ...all.data } : featureFilters

  const features = filters?.features ?? []
  const availableFeatures = features.filter(
    (feature) =>
      (!value.partId || feature.part_ids?.includes(value.partId)) &&
      (!value.category || feature.category === value.category) &&
      (!value.tag || feature.tags?.includes(value.tag)),
  )
  const selectedFeature = features.find(
    (feature) => feature.id === value.featureId,
  )
  const selectedPart = filters?.parts.find((part) => part.id === value.partId)
  const parts = (filters?.parts ?? []).filter(
    (part) => !value.featureId || selectedFeature?.part_ids?.includes(part.id),
  )
  const set = (patch: Partial<FeatureSearchState>) => {
    const next = { ...value, ...patch }
    const selected = features.find((feature) => feature.id === next.featureId)
    if (
      selected &&
      ((next.partId && !selected.part_ids?.includes(next.partId)) ||
        (next.category && selected.category !== next.category) ||
        (next.tag && !selected.tags?.includes(next.tag)))
    )
      next.featureId = null
    onChange(next)
  }
  const activeFilters = [
    {
      key: "partId" as const,
      label: "Pieza",
      text: selectedPart ? partLabel(selectedPart) : "Selección no disponible",
    },
    {
      key: "featureId" as const,
      label: "Feature",
      text: selectedFeature?.name ?? "Selección no disponible",
    },
    {
      key: "category" as const,
      label: "Categoría",
      text: value.category ? CATEGORY_LABELS[value.category] : "",
    },
    { key: "tag" as const, label: "Tag", text: value.tag },
  ].filter((filter) => value[filter.key])

  return (
    <div className="space-y-3">
      <SearchToolbar
        action={
          <Button
            type="button"
            variant="outline"
            className="h-11 shrink-0"
            aria-expanded={filtersOpen}
            aria-controls={filtersId}
            onClick={() => setFiltersOpen(!filtersOpen)}
          >
            <SlidersHorizontal className="size-4" /> Filtros
            {activeFilters.length ? ` (${activeFilters.length})` : ""}
          </Button>
        }
      >
        <SearchField
          className="h-11"
          value={value.q}
          onValueChange={(q) => set({ q })}
          placeholder={
            catalog
              ? "Buscar piezas, features o cotas…"
              : "Feature / pieza / codigo / tag..."
          }
          onClear={() => set({ q: "" })}
        />
      </SearchToolbar>
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {activeFilters.map((filter) => (
            <Button
              key={filter.key}
              type="button"
              variant="secondary"
              size="sm"
              className="h-7 max-w-full gap-1.5 rounded-full text-xs font-normal"
              aria-label={`Quitar filtro ${filter.label}: ${filter.text}`}
              onClick={() => set({ [filter.key]: null })}
            >
              <span className="truncate">
                {filter.label}: {filter.text}
              </span>
              <X className="size-3 shrink-0" />
            </Button>
          ))}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs font-normal text-muted-foreground"
            onClick={() => onChange({ ...EMPTY_SEARCH, q: value.q })}
          >
            Limpiar filtros
          </Button>
        </div>
      )}
      {filtersOpen && (
        <div
          id={filtersId}
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        >
          <SearchSelect
            showLabel
            label="Pieza"
            value={value.partId}
            placeholder="Todas las piezas"
            emptyLabel="Todas las piezas"
            selectedLabel={selectedPart ? partLabel(selectedPart) : undefined}
            options={parts.map((part) => ({
              value: part.id,
              label: partLabel(part),
            }))}
            onChange={(partId) => set({ partId: partId ?? null })}
          />
          <SearchSelect
            showLabel
            label="Feature"
            value={value.featureId}
            selectedLabel={selectedFeature?.name}
            placeholder="Todos los features"
            emptyLabel="Todos los features"
            options={availableFeatures.map((feature) => ({
              value: feature.id,
              label: feature.name,
            }))}
            onChange={(featureId) => set({ featureId: featureId ?? null })}
          />
          <SearchSelect
            showLabel
            label="Categoría"
            value={value.category}
            placeholder="Todas las categorías"
            emptyLabel="Todas las categorías"
            options={(filters?.categories ?? []).map((category) => ({
              value: category,
              label: CATEGORY_LABELS[category],
            }))}
            onChange={(category) =>
              set({ category: (category as FeatureCategory) ?? null })
            }
          />
          <SearchSelect
            showLabel
            label="Tag"
            value={value.tag}
            placeholder="Todos los tags"
            emptyLabel="Todos los tags"
            options={(filters?.tags ?? []).map((tag) => ({
              value: tag,
              label: tag,
            }))}
            onChange={(tag) => set({ tag: tag ?? null })}
          />
        </div>
      )}
    </div>
  )
}
