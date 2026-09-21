import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { ChevronRight, Package } from "lucide-react"
import { PartsService } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { fileErrorMessage } from "@/hooks/useFileAccess"

export const Route = createFileRoute("/_layout/parts")({
  component: Parts,
  validateSearch: (search: Record<string, unknown>): { q?: string } => ({
    q:
      typeof search.q === "string" || typeof search.q === "number"
        ? String(search.q) || undefined
        : undefined,
  }),
  head: () => ({ meta: [{ title: "Piezas - INTEPLAST" }] }),
})
function Parts() {
  const { q: search = "" } = Route.useSearch()
  const navigate = useNavigate()
  const setSearch = (q: string) =>
    void navigate({
      to: "/parts",
      search: { q: q || undefined },
      replace: true,
      resetScroll: false,
    })
  const parts = useQuery({
    queryKey: ["parts", "catalog"],
    queryFn: () => PartsService.readParts({ limit: 1000 }),
  })
  const visible =
    parts.data?.data.filter((p) =>
      `${p.code} ${p.name}`.toLowerCase().includes(search.toLowerCase()),
    ) ?? []
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">Piezas</h1>
      <SearchField
        aria-label="Buscar pieza"
        placeholder="Buscar por código o nombre…"
        value={search}
        onValueChange={setSearch}
        onClear={() => setSearch("")}
      />
      {parts.isPending ? (
        <p className="text-sm text-muted-foreground">Cargando piezas…</p>
      ) : parts.error ? (
        <p role="alert">{fileErrorMessage(parts.error)}</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((p) => (
            <Link
              to="/parts/$partId"
              params={{ partId: p.id }}
              key={p.id}
              className="flex items-center gap-4 rounded-lg border p-5 transition-colors hover:bg-accent/50"
            >
              <Package className="size-6 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <span className="font-mono text-sm font-semibold">
                  {p.code}
                </span>
                <h2 className="mt-1 truncate font-medium">{p.name}</h2>
                <p className="mt-2 text-xs text-muted-foreground">
                  {p.feature_count} features
                </p>
              </div>
              <ChevronRight className="size-4 text-muted-foreground" />
            </Link>
          ))}
        </div>
      )}
      {!parts.isPending && !parts.error && !visible.length && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No hay piezas para esta búsqueda.
        </p>
      )}
    </div>
  )
}
