import { useQuery } from "@tanstack/react-query"
import { useNavigate, useRouter } from "@tanstack/react-router"
import { lazy, Suspense, useRef } from "react"
import { EvidenceService } from "@/client"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { consultationScope } from "./consultationEntries"
import { DrawingToggle } from "./DrawingToggle"
import { Measurements } from "./Measurements"
import { MetrologyFilters } from "./MetrologyFilters"
import type { PartSearch } from "./measurementSelection"
import type { Study } from "./types"

const DrawingSearch = lazy(() => import("@/components/Features/DrawingSearch"))

export function MetrologyPage({
  partId,
  search,
}: {
  partId?: string
  search: PartSearch
}) {
  const navigate = useNavigate()
  const router = useRouter()
  const openedDrawing = useRef(false)
  const options = useQuery({
    queryKey: ["metrology-filters"],
    queryFn: () => EvidenceService.readMetrologyFilters(),
  })
  const result = useQuery({
    queryKey: ["part-evidence", partId],
    queryFn: () => EvidenceService.readPartEvidence({ partId: partId! }),
    enabled: Boolean(partId),
    refetchInterval: (q) =>
      ["queued", "processing"].includes(q.state.data?.study.state ?? "")
        ? 2500
        : false,
  })
  const visit = (
    id: string | undefined,
    values: PartSearch,
    replace = false,
  ) => {
    if (id)
      void navigate({
        to: "/parts/$partId",
        params: { partId: id },
        search: values,
        replace,
        resetScroll: false,
      })
    else
      void navigate({
        to: "/parts",
        search: values,
        replace,
        resetScroll: false,
      })
  }
  const change = (values: Partial<PartSearch>, replace = false) =>
    visit(partId, { ...search, ...values }, replace)
  const data = result.data
  const study =
    data?.study.state === "ready" ? (data.study.payload as Study) : undefined
  const scope = consultationScope(data?.features ?? [], search)
  const drawing =
    data?.documents.find(
      (document) =>
        document.id === search.drawingFile &&
        document.filename.toLowerCase().endsWith(".pdf"),
    ) ??
    data?.documents.find((document) =>
      /(?:DRW|plano|drawing).*\.pdf$/i.test(document.filename),
    )
  const filters = (
    <MetrologyFilters
      options={options.data}
      partId={partId}
      part={
        data?.part ?? options.data?.parts.find((part) => part.id === partId)
      }
      search={search}
      onPart={(id) => {
        openedDrawing.current = false
        visit(id, {
          feature: search.feature,
          category: search.category,
          tag: search.tag,
        })
      }}
      onScope={(values) => {
        openedDrawing.current = false
        visit(partId, {
          feature: search.feature,
          category: search.category,
          tag: search.tag,
          plano: search.plano,
          drawingFile: search.drawingFile,
          view: search.view,
          ...values,
        })
      }}
    />
  )
  const error = options.error ?? (partId ? result.error : null)
  const status =
    partId && result.isPending
      ? "Cargando cotas…"
      : ["queued", "processing"].includes(data?.study.state ?? "")
        ? "Preparando mediciones…"
        : data?.study.state === "error"
          ? data.study.message
          : undefined
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">Metrología</h1>
      {error && <p role="alert">{fileErrorMessage(error)}</p>}
      {search.plano && drawing ? (
        <Suspense
          fallback={
            <p className="text-sm text-muted-foreground">Cargando plano…</p>
          }
        >
          <DrawingSearch
            file={drawing}
            title={drawing.filename}
            initialQuery={search.drawingQ ?? search.cota ?? ""}
            onQueryChange={(drawingQ) => change({ drawingQ }, true)}
            searchFilters={filters}
            allowedCotas={
              scope === undefined
                ? undefined
                : (scope?.characteristics ?? []).map((cota) => cota.code)
            }
            searchAction={
              <DrawingToggle
                active
                onClick={() => {
                  if (openedDrawing.current) router.history.back()
                  else change({ plano: undefined, drawingQ: undefined }, true)
                }}
              />
            }
          />
        </Suspense>
      ) : (
        <Measurements
          study={study}
          characteristics={data?.characteristics ?? []}
          features={data?.features ?? []}
          status={status}
          filters={filters}
          partSelected={Boolean(partId)}
          search={
            partId
              ? search
              : {
                  feature: search.feature,
                  category: search.category,
                  tag: search.tag,
                }
          }
          onChange={change}
          onDrawing={
            drawing
              ? (code) => {
                  openedDrawing.current = true
                  change({ plano: true, drawingQ: code })
                }
              : undefined
          }
        />
      )}
    </div>
  )
}
