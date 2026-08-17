import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { LayoutList, Search, Users } from "lucide-react"
import { useState } from "react"

import { FeatureCard } from "@/components/Features/FeatureCard"
import { FeatureDetailDialog } from "@/components/Features/FeatureDetailDialog"
import {
  EMPTY_SEARCH,
  FeatureSearch,
  type FeatureSearchState,
  isSearchActive,
} from "@/components/Features/FeatureSearch"
import { featuresQueryOptions } from "@/components/Features/queries"
import PendingFeatures from "@/components/Pending/PendingFeatures"
import { Button } from "@/components/ui/button"
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
  head: () => ({
    meta: [
      {
        title: "Dashboard - INTEPLAST",
      },
    ],
  }),
})

const QUICK_ACCESS = [
  {
    icon: LayoutList,
    title: "Features",
    description: "Crea, edita o elimina fichas de features.",
    path: "/features",
    action: "Gestionar",
  },
  {
    icon: Users,
    title: "Admin",
    description: "Gestiona los usuarios y sus permisos de acceso.",
    path: "/admin",
    action: "Gestionar",
    superuserOnly: true,
  },
] as const

function Dashboard() {
  const { user: currentUser } = useAuth()
  const [search, setSearch] = useState<FeatureSearchState>(EMPTY_SEARCH)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const debouncedQuery = useDebounce(search.q)

  const searching = isSearchActive(search)
  const { data, isFetching } = useQuery(
    featuresQueryOptions({
      q: debouncedQuery || null,
      category: search.category,
      tag: search.tag,
      mold: search.mold,
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
            La busqueda mira tambien dentro de moldes, codigos de pieza,
            warnings y lessons learned.
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
                  onSelect={() => setSelectedId(feature.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {!searching && (
        <div className="grid gap-4 sm:grid-cols-2">
          {QUICK_ACCESS.filter(
            (entry) => !("superuserOnly" in entry) || currentUser?.is_superuser,
          ).map((entry) => (
            <Card key={entry.path}>
              <CardHeader>
                <entry.icon className="size-6 text-muted-foreground" />
                <CardTitle>{entry.title}</CardTitle>
                <CardDescription>{entry.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild>
                  <Link to={entry.path}>{entry.action}</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <FeatureDetailDialog
        featureId={selectedId}
        onOpenChange={(open) => !open && setSelectedId(null)}
      />
    </div>
  )
}
