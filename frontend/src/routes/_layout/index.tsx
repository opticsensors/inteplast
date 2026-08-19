import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { useEffect, useState } from "react"

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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"
import useDebounce from "@/hooks/useDebounce"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  validateSearch: validateFeatureSearch,
  head: () => ({
    meta: [
      {
        title: "Dashboard - INTEPLAST",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const navigate = useNavigate()
  // La URL manda al montar: asi volver desde la ficha devuelve los resultados
  const params = Route.useSearch()
  const [search, setSearch] = useState<FeatureSearchState>(() =>
    toSearchState(params),
  )
  const debouncedQuery = useDebounce(search.q)

  // ...y el estado se refleja de vuelta en la URL. `replace` para no dejar una
  // entrada de historial por cada tecla pulsada.
  useEffect(() => {
    navigate({
      to: "/",
      search: toSearchParams({
        q: debouncedQuery,
        category: search.category,
        tag: search.tag,
        partId: search.partId,
      }),
      replace: true,
    })
  }, [navigate, debouncedQuery, search.category, search.tag, search.partId])

  const searching = isSearchActive(search)
  const { data, isFetching } = useQuery(
    featuresQueryOptions({
      q: debouncedQuery || null,
      category: search.category,
      tag: search.tag,
      partId: search.partId,
      // Sin busqueda el dashboard solo enseña los ultimos features creados
      limit: searching ? 50 : 5,
    }),
  )

  const features = data?.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="max-w-sm truncate text-2xl font-bold tracking-tight">
          Hola, {currentUser?.full_name || currentUser?.email}
        </h1>
        <p className="text-muted-foreground">
          Busca un feature para ver sus warnings, lessons learned y piezas de
          referencia.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Resultados</CardTitle>
          <CardDescription>
            La busqueda mira tambien dentro de las piezas, los ficheros
            adjuntos, los warnings y las lessons learned.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FeatureSearch value={search} onChange={setSearch} />

          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{searching ? "Resultados" : "Recientes"}</span>
            <span>
              {data
                ? `${data.count} resultado${data.count === 1 ? "" : "s"}`
                : ""}
            </span>
          </div>

          {isFetching && features.length === 0 ? (
            <PendingFeatures />
          ) : features.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <div className="mb-3 rounded-full bg-muted p-4">
                <Search className="size-7 text-muted-foreground" />
              </div>
              <h3 className="font-semibold">
                {searching
                  ? "Ningun feature coincide con la busqueda"
                  : "Todavia no hay features"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {searching
                  ? "Prueba con otro termino o quita algun filtro."
                  : "Crea el primero desde la pagina de Features."}
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
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
