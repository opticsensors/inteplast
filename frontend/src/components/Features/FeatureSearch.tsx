import { useQuery } from "@tanstack/react-query"
import { SlidersHorizontal, X } from "lucide-react"
import { type ReactNode, useId, useState } from "react"

import { EvidenceService, type PartPublic } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { SearchSelect } from "@/components/Common/SearchSelect"
import { SearchToolbar } from "@/components/Common/SearchToolbar"
import { catalogNamesQueryOptions } from "@/components/Parts/CatalogNameSelect"
import { Button } from "@/components/ui/button"
import { partLabel } from "./parts"
import { featureFiltersQueryOptions } from "./queries"

export interface FeatureSearchState {
  q: string
  partId: string | null
  featureId: string | null
  familyId: string | null
  customerId: string | null
}

export const EMPTY_SEARCH: FeatureSearchState = {
  q: "",
  partId: null,
  featureId: null,
  familyId: null,
  customerId: null,
}

/**
 * La busqueda tambien vive en la URL (`/features?q=bolt&part=<id>`). Asi el boton de
 * atras del navegador devuelve los resultados al volver de la ficha, y una
 * busqueda se puede compartir o guardar en favoritos.
 */
export interface FeatureSearchParams {
  kind?: "all" | "part" | "feature" | "drawing"
  q?: string
  part?: string
  feature?: string
  family?: string
  customer?: string
}

/**
 * Nadie garantiza lo que llega en la URL: lo que no cuadre, fuera. Los enlaces
 * antiguos con `category` o `tag` se abren igual, sin esos filtros.
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

  return {
    kind:
      search.kind === "part" ||
      search.kind === "feature" ||
      search.kind === "drawing"
        ? search.kind
        : undefined,
    q: text(search.q),
    part: text(search.part),
    feature: text(search.feature),
    family: text(search.family),
    customer: text(search.customer),
  }
}

export const toSearchState = (
  params: FeatureSearchParams,
): FeatureSearchState => ({
  q: params.q ?? "",
  partId: params.part ?? null,
  featureId: params.feature ?? null,
  familyId: params.family ?? null,
  customerId: params.customer ?? null,
})

/** Los vacios se omiten para no arrastrar un `?q=&part=` por toda la app. */
export const toSearchParams = (
  state: FeatureSearchState,
): FeatureSearchParams => ({
  q: state.q || undefined,
  part: state.partId ?? undefined,
  feature: state.featureId ?? undefined,
  family: state.familyId ?? undefined,
  customer: state.customerId ?? undefined,
})

/** The same piece criterion as the server: every active piece filter at once. */
const pieceMatches = (
  part: Pick<PartPublic, "id" | "family_id" | "customer_id">,
  value: Pick<FeatureSearchState, "partId" | "familyId" | "customerId">,
) =>
  (!value.partId || part.id === value.partId) &&
  (!value.familyId || part.family_id === value.familyId) &&
  (!value.customerId || part.customer_id === value.customerId)

interface FeatureSearchProps {
  value: FeatureSearchState
  onChange: (value: FeatureSearchState) => void
  catalog?: boolean
  /** Controls placed beside the search, before Filtros (the catalogue's views). */
  actions?: ReactNode
}

/** Buscador global + filtros por pieza, feature, familia y cliente. */
export function FeatureSearch({
  value,
  onChange,
  catalog = false,
  actions,
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
  const families = useQuery(catalogNamesQueryOptions("families"))
  const customers = useQuery(catalogNamesQueryOptions("customers"))
  const filters =
    catalog && all.data ? { ...featureFilters, ...all.data } : featureFilters

  const allParts = filters?.parts ?? []
  const features = filters?.features ?? []
  const pieceFilters = Boolean(
    value.partId || value.familyId || value.customerId,
  )
  const matchingParts = new Set(
    allParts.filter((part) => pieceMatches(part, value)).map((part) => part.id),
  )
  const availableFeatures = features.filter(
    (feature) =>
      !pieceFilters ||
      (feature.part_ids ?? []).some((id) => matchingParts.has(id)),
  )
  const selectedFeature = features.find(
    (feature) => feature.id === value.featureId,
  )
  const selectedPart = allParts.find((part) => part.id === value.partId)
  const parts = allParts.filter(
    (part) =>
      pieceMatches(part, { ...value, partId: null }) &&
      (!value.featureId || selectedFeature?.part_ids?.includes(part.id)),
  )
  const familyName = families.data?.data.find(
    (item) => item.id === value.familyId,
  )?.name
  const customerName = customers.data?.data.find(
    (item) => item.id === value.customerId,
  )?.name
  const set = (patch: Partial<FeatureSearchState>) => {
    const next = { ...value, ...patch }
    const part = allParts.find((item) => item.id === next.partId)
    if (part && !pieceMatches(part, { ...next, partId: null }))
      next.partId = null
    const selected = features.find((feature) => feature.id === next.featureId)
    const stillMatching = new Set(
      allParts
        .filter((item) => pieceMatches(item, next))
        .map((item) => item.id),
    )
    if (
      selected &&
      (next.partId || next.familyId || next.customerId) &&
      !(selected.part_ids ?? []).some((id) => stillMatching.has(id))
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
      key: "familyId" as const,
      label: "Familia",
      text: familyName ?? "Selección no disponible",
    },
    {
      key: "customerId" as const,
      label: "Cliente",
      text: customerName ?? "Selección no disponible",
    },
  ].filter((filter) => value[filter.key])

  return (
    <div className="space-y-3">
      <SearchToolbar
        action={
          <div className="flex shrink-0 items-start gap-2">
            {actions}
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
          </div>
        }
      >
        <SearchField
          className="h-11"
          value={value.q}
          onValueChange={(q) => set({ q })}
          placeholder={
            catalog
              ? "Buscar piezas, features o cotas…"
              : "Feature / pieza / codigo..."
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
            label="Familia"
            value={value.familyId}
            selectedLabel={familyName}
            placeholder="Todas las familias"
            emptyLabel="Todas las familias"
            options={(families.data?.data ?? []).map((item) => ({
              value: item.id,
              label: item.name,
            }))}
            onChange={(familyId) => set({ familyId: familyId ?? null })}
          />
          <SearchSelect
            showLabel
            label="Cliente"
            value={value.customerId}
            selectedLabel={customerName}
            placeholder="Todos los clientes"
            emptyLabel="Todos los clientes"
            options={(customers.data?.data ?? []).map((item) => ({
              value: item.id,
              label: item.name,
            }))}
            onChange={(customerId) => set({ customerId: customerId ?? null })}
          />
        </div>
      )}
    </div>
  )
}
