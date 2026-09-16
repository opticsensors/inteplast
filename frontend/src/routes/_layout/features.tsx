import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Plus, Search } from "lucide-react"

import { FeatureActions } from "@/components/Features/FeatureActions"
import { FeatureCard } from "@/components/Features/FeatureCard"
import {
  FeatureSearch,
  type FeatureSearchState,
  isSearchActive,
  toSearchParams,
  toSearchState,
  validateFeatureSearch,
} from "@/components/Features/FeatureSearch"
import { featuresQueryOptions } from "@/components/Features/queries"
import PendingFeatures from "@/components/Pending/PendingFeatures"
import { Button } from "@/components/ui/button"
import useDebounce from "@/hooks/useDebounce"

export const Route = createFileRoute("/_layout/features")({
  component: Features,
  validateSearch: validateFeatureSearch,
  head: () => ({
    meta: [
      {
        title: "Features - INTEPLAST",
      },
    ],
  }),
})

function Features() {
  const navigate = useNavigate()
  const params = Route.useSearch()
  const search = toSearchState(params)
  const debouncedQuery = useDebounce(search.q)

  // La URL conserva los filtros al volver desde una ficha o un favorito.
  // El debounce solo retrasa la consulta; no deja navegaciones pendientes.
  const setSearch = (next: FeatureSearchState) =>
    navigate({
      to: "/features",
      search: toSearchParams(next),
      replace: true,
      resetScroll: false,
    })

  const editFeature = (featureId: string) =>
    navigate({
      to: "/features/$featureId",
      params: { featureId },
      search: { editar: true },
    })

  const { data, isPending } = useQuery(
    featuresQueryOptions({
      q: debouncedQuery || null,
      category: search.category,
      tag: search.tag,
      partId: search.partId,
    }),
  )

  const features = data?.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">Features</h1>
        <Button onClick={() => navigate({ to: "/features/nuevo" })}>
          <Plus />
          Nuevo feature
        </Button>
      </div>

      <FeatureSearch value={search} onChange={setSearch} />

      {isPending ? (
        <PendingFeatures />
      ) : features.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 rounded-full bg-muted p-4">
            <Search className="size-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">
            {isSearchActive(search)
              ? "Ningún feature coincide con la búsqueda"
              : "Todavía no hay features"}
          </h3>
          <p className="text-muted-foreground">
            {isSearchActive(search)
              ? "Prueba con otro término o quita algún filtro."
              : "Crea el primero con Nuevo feature."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {features.map((feature) => (
            <FeatureCard
              key={feature.id}
              feature={feature}
              onSelect={() =>
                navigate({
                  to: "/features/$featureId",
                  params: { featureId: feature.id },
                })
              }
              actions={
                <FeatureActions onEdit={() => editFeature(feature.id)} />
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
