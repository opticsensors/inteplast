import { useQuery } from "@tanstack/react-query"
import { SlidersHorizontal } from "lucide-react"
import { useId, useState } from "react"

import type { FeatureCategory } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { SearchSelect } from "@/components/Common/SearchSelect"
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

export const isSearchActive = (state: FeatureSearchState) =>
  Boolean(
    state.q || state.category || state.tag || state.partId || state.featureId,
  )

/**
 * La busqueda tambien vive en la URL (`/features?q=bolt&part=<id>`). Asi el boton de
 * atras del navegador devuelve los resultados al volver de la ficha, y una
 * busqueda se puede compartir o guardar en favoritos.
 */
export interface FeatureSearchParams {
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
}

/** Buscador global + filtros por pieza, feature, categoria y tag. */
export function FeatureSearch({ value, onChange }: FeatureSearchProps) {
  const [more, setMore] = useState(Boolean(value.category || value.tag))
  const moreId = useId()
  const active = Number(Boolean(value.category)) + Number(Boolean(value.tag))
  // Solo se ofrecen los valores que existen en la base de datos
  const { data: filters } = useQuery(featureFiltersQueryOptions())

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

  return (
    <div className="space-y-3">
      <SearchField
        value={value.q}
        onValueChange={(q) => set({ q })}
        placeholder="Feature / pieza / codigo / tag..."
        active={isSearchActive(value)}
        onClear={() => onChange(EMPTY_SEARCH)}
      />

      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
        <SearchSelect
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
        <Button
          type="button"
          variant="outline"
          className="h-9 font-normal"
          aria-expanded={more}
          aria-controls={moreId}
          onClick={() => setMore(!more)}
        >
          <SlidersHorizontal className="size-4" /> Más filtros
          {active ? ` (${active})` : ""}
        </Button>
      </div>
      {more && (
        <div id={moreId} className="grid gap-2 sm:grid-cols-2">
          <SearchSelect
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
