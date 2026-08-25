import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Plus, Search } from "lucide-react"
import { useEffect, useState } from "react"

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
  const [search, setSearch] = useState<FeatureSearchState>(() =>
    toSearchState(params),
  )
  const debouncedQuery = useDebounce(search.q)

  // Aqui se viene a mantener la base, no a consultarla: el unico destino de
  // una tarjeta es su formulario. Consultar la ficha es cosa del dashboard.
  const editFeature = (featureId: string) =>
    navigate({
      to: "/features/$featureId",
      params: { featureId },
      search: { editar: true },
    })

  // Igual que en el dashboard: la busqueda vive en la URL para sobrevivir al
  // viaje de ida y vuelta a la ficha del feature.
  useEffect(() => {
    navigate({
      to: "/features",
      search: toSearchParams({
        q: debouncedQuery,
        category: search.category,
        tag: search.tag,
        partId: search.partId,
      }),
      replace: true,
    })
  }, [navigate, debouncedQuery, search.category, search.tag, search.partId])

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Features</h1>
          <p className="text-muted-foreground">
            Crea y mantiene las fichas de la base de conocimiento.
          </p>
        </div>
        <Button onClick={() => navigate({ to: "/features/nuevo" })}>
          <Plus className="mr-2" />
          Anadir feature
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
              ? "Ningun feature coincide con la busqueda"
              : "Todavia no hay features"}
          </h3>
          <p className="text-muted-foreground">
            {isSearchActive(search)
              ? "Prueba con otro termino o quita algun filtro."
              : "Anade el primero para empezar."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {features.map((feature) => (
            <FeatureCard
              key={feature.id}
              feature={feature}
              // La tarjeta no se clica: lo unico que se puede pulsar son sus
              // dos botones. Clicarla llevaba a una ficha de solo lectura con
              // estos mismos dos botones arriba, un paso de mas para nada.
              actions={
                <FeatureActions
                  featureId={feature.id}
                  onEdit={() => editFeature(feature.id)}
                />
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
