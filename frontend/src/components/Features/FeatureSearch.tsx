import { useQuery } from "@tanstack/react-query"
import { Search, X } from "lucide-react"

import type { FeatureCategory } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { CATEGORIES, CATEGORY_LABELS } from "./constants"
import { partLabel } from "./parts"
import { featureFiltersQueryOptions } from "./queries"

export interface FeatureSearchState {
  q: string
  category: FeatureCategory | null
  tag: string | null
  partId: string | null
}

export const EMPTY_SEARCH: FeatureSearchState = {
  q: "",
  category: null,
  tag: null,
  partId: null,
}

export const isSearchActive = (state: FeatureSearchState) =>
  Boolean(state.q || state.category || state.tag || state.partId)

/**
 * La busqueda tambien vive en la URL (`/?q=bolt&part=<id>`). Asi el boton de
 * atras del navegador devuelve los resultados al volver de la ficha, y una
 * busqueda se puede compartir o guardar en favoritos.
 */
export interface FeatureSearchParams {
  q?: string
  category?: FeatureCategory
  tag?: string
  part?: string
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
  }
}

export const toSearchState = (
  params: FeatureSearchParams,
): FeatureSearchState => ({
  q: params.q ?? "",
  category: params.category ?? null,
  tag: params.tag ?? null,
  partId: params.part ?? null,
})

/** Los vacios se omiten para no arrastrar un `?q=&tag=` por toda la app. */
export const toSearchParams = (
  state: FeatureSearchState,
): FeatureSearchParams => ({
  q: state.q || undefined,
  category: state.category ?? undefined,
  tag: state.tag ?? undefined,
  part: state.partId ?? undefined,
})

const ALL = "all"

interface FeatureSearchProps {
  value: FeatureSearchState
  onChange: (value: FeatureSearchState) => void
}

/** Buscador global + filtros por pieza, categoria y tag. */
export function FeatureSearch({ value, onChange }: FeatureSearchProps) {
  // Solo se ofrecen los valores que existen en la base de datos
  const { data: filters } = useQuery(featureFiltersQueryOptions())

  const set = (patch: Partial<FeatureSearchState>) =>
    onChange({ ...value, ...patch })

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value.q}
          onChange={(event) => set({ q: event.target.value })}
          placeholder="Feature / pieza / codigo / tag..."
          className="pl-9"
        />
        {isSearchActive(value) && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-1/2 right-1 size-7 -translate-y-1/2"
            onClick={() => onChange(EMPTY_SEARCH)}
          >
            <X className="size-4" />
            <span className="sr-only">Limpiar busqueda</span>
          </Button>
        )}
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <Select
          value={value.partId ?? ALL}
          onValueChange={(next) => set({ partId: next === ALL ? null : next })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Pieza" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todas las piezas</SelectItem>
            {(filters?.parts ?? []).map((part) => (
              <SelectItem key={part.id} value={part.id}>
                {partLabel(part)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={value.category ?? ALL}
          onValueChange={(next) =>
            set({ category: next === ALL ? null : (next as FeatureCategory) })
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todas las categorias</SelectItem>
            {(filters?.categories ?? []).map((category) => (
              <SelectItem key={category} value={category}>
                {CATEGORY_LABELS[category]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={value.tag ?? ALL}
          onValueChange={(next) => set({ tag: next === ALL ? null : next })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Tag" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los tags</SelectItem>
            {(filters?.tags ?? []).map((tag) => (
              <SelectItem key={tag} value={tag}>
                {tag}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
