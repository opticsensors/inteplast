import { useInfiniteQuery } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { Plus, Ruler, Search } from "lucide-react"
import { lazy, Suspense, useState } from "react"
import { CatalogService } from "@/client"
import { FeatureActions } from "@/components/Features/FeatureActions"
import { FeatureCard } from "@/components/Features/FeatureCard"
import {
  FeatureSearch,
  type FeatureSearchParams,
  toSearchParams,
  toSearchState,
} from "@/components/Features/FeatureSearch"
import { partLabel } from "@/components/Features/parts"
import { PartCard } from "@/components/Parts/PartCard"
import PendingFeatures from "@/components/Pending/PendingFeatures"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import useDebounce from "@/hooks/useDebounce"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { CatalogDrawings } from "./CatalogDrawings"
import { FeatureTile, PartTile } from "./CatalogTiles"

// The graph library loads only when the graph view is opened.
const CatalogGraph = lazy(() => import("./CatalogGraph"))

import {
  type CatalogView,
  CatalogViewSwitch,
  readCatalogView,
  saveCatalogView,
} from "./CatalogView"

export function CatalogPage({ params }: { params: FeatureSearchParams }) {
  const navigate = useNavigate()
  const search = toSearchState(params)
  const [view, setView] = useState<CatalogView>(readCatalogView)
  const changeView = (next: CatalogView) => {
    setView(next)
    saveCatalogView(next)
    if (next === "graph" && params.kind && params.kind !== "all")
      change({ ...params, kind: "all" })
  }
  const q = useDebounce(search.q)
  const kind =
    view === "graph" && params.kind !== "drawing"
      ? "all"
      : (params.kind ?? "all")
  // «Planos» has its own list and is always a grid.
  const drawings = kind === "drawing"
  const change = (values: FeatureSearchParams) =>
    void navigate({
      to: "/features",
      search: values,
      replace: true,
      resetScroll: false,
    })
  const request = {
    q,
    kind: drawings ? ("all" as const) : kind,
    partId: search.partId,
    featureId: search.featureId,
    familyId: search.familyId,
    customerId: search.customerId,
  }
  const result = useInfiniteQuery({
    queryKey: ["features", "catalog", request],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      CatalogService.searchCatalog({ ...request, skip: pageParam, limit: 40 }),
    enabled: !drawings,
    getNextPageParam: (last, pages) =>
      pages.length * 40 <
      Math.max(last.feature_count, last.part_count, last.cota_count)
        ? pages.length * 40
        : undefined,
  })
  const pages = result.data?.pages ?? []
  const cards = pages
    .flatMap((page) => [
      ...page.parts.map((part) => ({
        kind: "part" as const,
        id: part.id,
        // The code is the piece's title: order by it, as the card shows it.
        name: partLabel(part),
        part,
      })),
      ...page.features.map((feature) => ({
        kind: "feature" as const,
        id: feature.id,
        name: feature.name,
        feature,
      })),
    ])
    .sort(
      (a, b) =>
        a.name.localeCompare(b.name, "es", { numeric: true }) ||
        a.id.localeCompare(b.id),
    )
  const cotas = pages.flatMap((page) => page.cotas)
  const cotaTotal = pages[0]?.cota_count ?? 0
  const partSearch = { feature: params.feature }
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Catálogo</h1>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            className="h-11"
            onClick={() => void navigate({ to: "/features/nuevo" })}
          >
            <Plus />
            Nuevo feature
          </Button>
          <Button
            className="h-11"
            onClick={() => void navigate({ to: "/parts/nueva" })}
          >
            <Plus />
            Nueva pieza
          </Button>
        </div>
      </div>
      <div className="space-y-4">
        <fieldset
          className="flex gap-6 border-b"
          aria-label="Tipo de resultado"
        >
          {(
            [
              ["all", "Todo"],
              ["part", "Piezas"],
              ["feature", "Features"],
              ["drawing", "Planos"],
            ] as const
          ).map(([value, label]) => (
            <Button
              key={value}
              variant="ghost"
              className="-mb-px h-11 rounded-none border-b-2 border-transparent px-0 text-muted-foreground hover:bg-transparent hover:text-foreground aria-pressed:border-primary aria-pressed:text-primary"
              aria-pressed={kind === value}
              onClick={() => {
                if (
                  view === "graph" &&
                  (value === "part" || value === "feature")
                )
                  changeView("list")
                change({ ...params, kind: value })
              }}
            >
              {label}
            </Button>
          ))}
        </fieldset>
        <FeatureSearch
          catalog
          value={search}
          onChange={(next) => change({ ...toSearchParams(next), kind })}
          actions={
            drawings ? undefined : (
              <CatalogViewSwitch value={view} onChange={changeView} />
            )
          }
        />
      </div>
      {drawings ? (
        <CatalogDrawings
          request={{
            q,
            partId: search.partId,
            featureId: search.featureId,
            familyId: search.familyId,
            customerId: search.customerId,
          }}
          onOpen={(card) =>
            void navigate({
              to: "/parts/$partId/fichero/$fileId",
              params: { partId: card.part.id, fileId: card.file.id },
            })
          }
        />
      ) : result.isPending ? (
        <PendingFeatures />
      ) : result.error ? (
        <p role="alert">{fileErrorMessage(result.error)}</p>
      ) : (
        <>
          {q.trim() && cotas.length > 0 && (
            <section aria-label="Cotas encontradas" className="space-y-2">
              <h2 className="text-lg font-semibold">Cotas</h2>
              <div className="grid gap-2 sm:grid-cols-2">
                {cotas.map((cota) => (
                  <Link
                    key={cota.id}
                    to="/parts/$partId"
                    params={{ partId: cota.part.id }}
                    search={{
                      cota: cota.code,
                      q: cota.code,
                      revision: cota.revision,
                      feature: params.feature,
                    }}
                    hash="cotas"
                    className="flex min-w-0 items-center gap-3 rounded-md border p-3 text-sm hover:bg-accent/50"
                  >
                    <Ruler className="size-4 shrink-0 text-muted-foreground" />
                    <span className="font-semibold">{cota.code}</span>
                    <span className="min-w-0 truncate text-muted-foreground">
                      {partLabel(cota.part)} · rev. {cota.revision}
                    </span>
                  </Link>
                ))}
              </div>
              {/* The graph loads all pieces and features at once; only the cotas page. */}
              {view === "graph" && cotas.length < cotaTotal && (
                <Button
                  variant="outline"
                  disabled={result.isFetchingNextPage}
                  onClick={() => void result.fetchNextPage()}
                >
                  {result.isFetchingNextPage
                    ? "Cargando…"
                    : `Mostrar más cotas (${cotas.length} de ${cotaTotal})`}
                </Button>
              )}
            </section>
          )}
          {view === "graph" ? (
            <Suspense fallback={<Skeleton className="h-96 w-full" />}>
              <CatalogGraph
                request={{
                  q,
                  kind,
                  partId: search.partId,
                  featureId: search.featureId,
                  familyId: search.familyId,
                  customerId: search.customerId,
                }}
                onOpen={(node) =>
                  node.kind === "part"
                    ? void navigate({
                        to: "/parts/$partId",
                        params: { partId: node.ref_id },
                        search: partSearch,
                      })
                    : void navigate({
                        to: "/features/$featureId",
                        params: { featureId: node.ref_id },
                      })
                }
                onFilter={(group, id) =>
                  change({
                    ...params,
                    [group]: id,
                  })
                }
              />
            </Suspense>
          ) : (
            <>
              <div
                className={
                  view === "grid"
                    ? "grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
                    : "space-y-2"
                }
                data-view={view}
              >
                {cards.map((card) => {
                  const open = () =>
                    card.kind === "part"
                      ? void navigate({
                          to: "/parts/$partId",
                          params: { partId: card.id },
                          search: partSearch,
                        })
                      : void navigate({
                          to: "/features/$featureId",
                          params: { featureId: card.id },
                        })
                  const actions = (
                    <FeatureActions
                      key={`actions-${card.id}`}
                      onEdit={() =>
                        card.kind === "part"
                          ? void navigate({
                              to: "/parts/$partId",
                              params: { partId: card.id },
                              search: { ...partSearch, editar: true },
                            })
                          : void navigate({
                              to: "/features/$featureId",
                              params: { featureId: card.id },
                              search: { editar: true },
                            })
                      }
                    />
                  )
                  if (card.kind === "part")
                    return view === "grid" ? (
                      <PartTile
                        key={`part-${card.id}`}
                        part={card.part}
                        onSelect={open}
                        actions={actions}
                      />
                    ) : (
                      <PartCard
                        key={`part-${card.id}`}
                        part={card.part}
                        onSelect={open}
                        actions={actions}
                      />
                    )
                  return view === "grid" ? (
                    <FeatureTile
                      key={`feature-${card.id}`}
                      feature={card.feature}
                      onSelect={open}
                      actions={actions}
                    />
                  ) : (
                    <FeatureCard
                      key={`feature-${card.id}`}
                      feature={card.feature}
                      showKind
                      onSelect={open}
                      actions={actions}
                    />
                  )
                })}
              </div>
              {!cards.length && !cotas.length && (
                <div className="flex flex-col items-center gap-3 py-12 text-center">
                  <Search className="size-8 text-muted-foreground" />
                  <p className="text-lg font-semibold">
                    {q ||
                    search.partId ||
                    search.featureId ||
                    search.familyId ||
                    search.customerId
                      ? "No hay resultados"
                      : "Todavía no hay piezas ni features"}
                  </p>
                </div>
              )}
              {result.hasNextPage && (
                <Button
                  variant="outline"
                  disabled={result.isFetchingNextPage}
                  onClick={() => void result.fetchNextPage()}
                >
                  {result.isFetchingNextPage ? "Cargando…" : "Mostrar más"}
                </Button>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
