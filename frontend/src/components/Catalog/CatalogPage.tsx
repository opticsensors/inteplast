import { useInfiniteQuery } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { Plus, Ruler, Search } from "lucide-react"
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
import { PartSetupDialog } from "@/components/Parts/PartSetupDialog"
import PendingFeatures from "@/components/Pending/PendingFeatures"
import { Button } from "@/components/ui/button"
import useDebounce from "@/hooks/useDebounce"
import { fileErrorMessage } from "@/hooks/useFileAccess"

export function CatalogPage({ params }: { params: FeatureSearchParams }) {
  const navigate = useNavigate()
  const search = toSearchState(params)
  const q = useDebounce(search.q)
  const kind = params.kind ?? "all"
  const change = (values: FeatureSearchParams) =>
    void navigate({
      to: "/features",
      search: values,
      replace: true,
      resetScroll: false,
    })
  const request = {
    q,
    kind,
    category: search.category,
    tag: search.tag,
    partId: search.partId,
    featureId: search.featureId,
  }
  const result = useInfiniteQuery({
    queryKey: ["features", "catalog", request],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      CatalogService.searchCatalog({ ...request, skip: pageParam, limit: 40 }),
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
        name: part.name ?? part.code,
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
  const partSearch = {
    feature: params.feature,
    category: params.category,
    tag: params.tag,
  }
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Catálogo</h1>
        <div className="flex flex-wrap gap-2">
          <PartSetupDialog
            onCreated={(partId) =>
              void navigate({ to: "/parts/$partId", params: { partId } })
            }
          />
          <Button onClick={() => void navigate({ to: "/features/nuevo" })}>
            <Plus />
            Nuevo feature
          </Button>
        </div>
      </div>
      <FeatureSearch
        catalog
        value={search}
        onChange={(next) => change({ ...toSearchParams(next), kind })}
      >
        <fieldset className="flex gap-2" aria-label="Tipo de resultado">
          {(
            [
              ["all", "Todo"],
              ["part", "Piezas"],
              ["feature", "Features"],
            ] as const
          ).map(([value, label]) => (
            <Button
              key={value}
              variant={kind === value ? "secondary" : "ghost"}
              size="sm"
              aria-pressed={kind === value}
              onClick={() => change({ ...params, kind: value })}
            >
              {label}
            </Button>
          ))}
        </fieldset>
      </FeatureSearch>
      {result.isPending ? (
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
                      category: params.category,
                      tag: params.tag,
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
            </section>
          )}
          <div className="space-y-2">
            {cards.map((card) =>
              card.kind === "part" ? (
                <PartCard
                  key={`part-${card.id}`}
                  part={card.part}
                  onSelect={() =>
                    void navigate({
                      to: "/parts/$partId",
                      params: { partId: card.id },
                      search: partSearch,
                    })
                  }
                  actions={
                    <FeatureActions
                      onEdit={() =>
                        void navigate({
                          to: "/parts/$partId",
                          params: { partId: card.id },
                          search: { ...partSearch, editar: true },
                        })
                      }
                    />
                  }
                />
              ) : (
                <FeatureCard
                  key={`feature-${card.id}`}
                  feature={card.feature}
                  showKind
                  onSelect={() =>
                    void navigate({
                      to: "/features/$featureId",
                      params: { featureId: card.id },
                    })
                  }
                  actions={
                    <FeatureActions
                      onEdit={() =>
                        void navigate({
                          to: "/features/$featureId",
                          params: { featureId: card.id },
                          search: { editar: true },
                        })
                      }
                    />
                  }
                />
              ),
            )}
          </div>
          {!cards.length && !cotas.length && (
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <Search className="size-8 text-muted-foreground" />
              <p className="text-lg font-semibold">
                {q ||
                search.partId ||
                search.featureId ||
                search.category ||
                search.tag
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
    </div>
  )
}
