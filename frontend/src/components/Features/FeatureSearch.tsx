import { useQuery } from "@tanstack/react-query"
import { SlidersHorizontal, X } from "lucide-react"
import { type ReactNode, useId, useRef, useState } from "react"

import { EvidenceService, type PartPublic } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { SearchSelect } from "@/components/Common/SearchSelect"
import { SearchToolbar } from "@/components/Common/SearchToolbar"
import { catalogNamesQueryOptions } from "@/components/Parts/CatalogNameSelect"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { partLabel } from "./parts"
import { featureFiltersQueryOptions } from "./queries"

export interface FeatureSearchState {
  q: string
  partId: string | null
  featureId: string | null
  familyId: string | null
  customerId: string | null
  materialId: string | null
}

export const EMPTY_SEARCH: FeatureSearchState = {
  q: "",
  partId: null,
  featureId: null,
  familyId: null,
  customerId: null,
  materialId: null,
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
  material?: string
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
    material: text(search.material),
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
  materialId: params.material ?? null,
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
  material: state.materialId ?? undefined,
})

/** The same piece criterion as the server: every active piece filter at once. */
const pieceMatches = (
  part: Pick<PartPublic, "id" | "family_id" | "customer_id" | "material_id">,
  value: Pick<
    FeatureSearchState,
    "partId" | "familyId" | "customerId" | "materialId"
  >,
) =>
  (!value.partId || part.id === value.partId) &&
  (!value.familyId || part.family_id === value.familyId) &&
  (!value.customerId || part.customer_id === value.customerId) &&
  (!value.materialId || part.material_id === value.materialId)

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
  const toggleRef = useRef<HTMLButtonElement>(null)
  // Solo se ofrecen los valores que existen en la base de datos
  const { data: featureFilters } = useQuery(featureFiltersQueryOptions())
  const all = useQuery({
    queryKey: ["metrology-filters"],
    queryFn: () => EvidenceService.readMetrologyFilters(),
    enabled: catalog,
  })
  const families = useQuery(catalogNamesQueryOptions("families"))
  const customers = useQuery(catalogNamesQueryOptions("customers"))
  const materials = useQuery(catalogNamesQueryOptions("materials"))
  const filters =
    catalog && all.data ? { ...featureFilters, ...all.data } : featureFilters

  const allParts = filters?.parts ?? []
  const features = filters?.features ?? []
  const pieceFilters = Boolean(
    value.partId || value.familyId || value.customerId || value.materialId,
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
  const materialName = materials.data?.data.find(
    (item) => item.id === value.materialId,
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
      (next.partId || next.familyId || next.customerId || next.materialId) &&
      !(selected.part_ids ?? []).some((id) => stillMatching.has(id))
    )
      next.featureId = null
    onChange(next)
  }
  const activeCount = [
    value.partId,
    value.featureId,
    value.familyId,
    value.customerId,
    value.materialId,
  ].filter(Boolean).length

  return (
    <div className="space-y-3">
      <SearchToolbar
        action={
          <div className="flex shrink-0 items-start gap-2">
            {actions}
            <ButtonGroup aria-label="Filtros del catálogo">
              <Button
                ref={toggleRef}
                type="button"
                variant="outline"
                className="h-11"
                aria-expanded={filtersOpen}
                aria-controls={filtersOpen ? filtersId : undefined}
                onClick={() => setFiltersOpen((open) => !open)}
              >
                <SlidersHorizontal className="size-4" /> Filtros
                {activeCount > 0 && ` (${activeCount})`}
              </Button>
              {activeCount > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-11 w-9 text-muted-foreground"
                  aria-label="Limpiar filtros"
                  title="Limpiar filtros"
                  onClick={() => {
                    onChange({ ...EMPTY_SEARCH, q: value.q })
                    setFiltersOpen(false)
                    toggleRef.current?.focus()
                  }}
                >
                  <X className="size-4" />
                </Button>
              )}
            </ButtonGroup>
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
      {filtersOpen && (
        <div
          id={filtersId}
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
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
          <SearchSelect
            showLabel
            label="Material"
            value={value.materialId}
            selectedLabel={materialName}
            placeholder="Todos los materiales"
            emptyLabel="Todos los materiales"
            options={(materials.data?.data ?? []).map((item) => ({
              value: item.id,
              label: item.name,
            }))}
            onChange={(materialId) => set({ materialId: materialId ?? null })}
          />
        </div>
      )}
    </div>
  )
}
