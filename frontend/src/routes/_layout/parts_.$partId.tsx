import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useRouter } from "@tanstack/react-router"
import { lazy, Suspense, useRef } from "react"
import { EvidenceService } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { SearchToolbar } from "@/components/Common/SearchToolbar"
import { DrawingToggle } from "@/components/Parts/DrawingToggle"
import { Measurements } from "@/components/Parts/Measurements"
import {
  type PartSearch,
  validatePartSearch,
} from "@/components/Parts/measurementSelection"
import type { Study } from "@/components/Parts/types"
import { fileErrorMessage } from "@/hooks/useFileAccess"

const DrawingSearch = lazy(() => import("@/components/Features/DrawingSearch"))

export const Route = createFileRoute("/_layout/parts_/$partId")({
  component: PartDetail,
  validateSearch: validatePartSearch,
  head: () => ({ meta: [{ title: "Cotas de la pieza - INTEPLAST" }] }),
})
export function partEvidenceQuery(partId: string) {
  return {
    queryKey: ["part-evidence", partId],
    queryFn: () => EvidenceService.readPartEvidence({ partId }),
  }
}
function PartDetail() {
  const { partId } = Route.useParams()
  const search = Route.useSearch()
  const navigate = useNavigate()
  const router = useRouter()
  const openedDrawing = useRef(false)
  const result = useQuery({
    ...partEvidenceQuery(partId),
    refetchInterval: (q) =>
      ["queued", "processing"].includes(q.state.data?.study.state ?? "")
        ? 2500
        : false,
  })
  if (result.isPending)
    return <p className="text-sm text-muted-foreground">Cargando pieza…</p>
  if (result.error || !result.data)
    return <p role="alert">{fileErrorMessage(result.error)}</p>
  const { part, study: job, documents } = result.data
  const study = job.state === "ready" ? (job.payload as Study) : undefined
  const busy = ["queued", "processing"].includes(job.state)
  const drawing = documents.find((document) =>
    /(?:DRW|plano|drawing).*\.pdf$/i.test(document.filename),
  )
  const onDrawing = drawing
    ? (code: string) => {
        openedDrawing.current = true
        change({ plano: true, drawingQ: code })
      }
    : undefined
  const change = (values: Partial<PartSearch>, replace = false) =>
    void navigate({
      to: "/parts/$partId",
      params: { partId },
      search: {
        q: search.q,
        cota: search.cota,
        element: search.element,
        height: search.height,
        evaluation: search.evaluation,
        cavities: search.cavities,
        interval: search.interval,
        action: search.action,
        cavity: search.cavity,
        view: search.view,
        plano: search.plano,
        drawingQ: search.drawingQ,
        ...values,
      },
      replace,
      resetScroll: false,
    })
  const closeDrawing = () => {
    // An in-page toggle returns to its consultation; a direct URL has no such history.
    if (openedDrawing.current) router.history.back()
    else change({ plano: undefined, drawingQ: undefined }, true)
  }
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            <span className="mr-3 font-mono">{part.code}</span>
            {part.name}
          </h1>
        </div>
      </div>
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
            searchAction={<DrawingToggle active onClick={closeDrawing} />}
          />
        </Suspense>
      ) : study ? (
        <Measurements
          study={study}
          search={search}
          onChange={change}
          onDrawing={onDrawing}
        />
      ) : (
        <div className="space-y-5">
          <SearchToolbar
            action={
              <DrawingToggle
                disabled={!onDrawing}
                onClick={() => onDrawing?.(search.q ?? search.cota ?? "")}
              />
            }
          >
            <SearchField
              aria-label="Buscar cota"
              placeholder="Buscar cota por número o descripción…"
              value={search.q ?? search.cota ?? ""}
              onValueChange={(q) => change({ q }, true)}
              onClear={() => change({ q: "" }, true)}
            />
          </SearchToolbar>
          <div className="rounded-lg border p-8 text-center text-sm text-muted-foreground">
            <p>
              {busy
                ? "Preparando mediciones…"
                : job.state === "error"
                  ? job.message
                  : "Todavía no hay mediciones incorporadas para esta pieza."}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
