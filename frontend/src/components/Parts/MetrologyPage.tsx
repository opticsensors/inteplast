import { useQuery } from "@tanstack/react-query"
import { Navigate, useNavigate } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { EvidenceService } from "@/client"
import { FilterSelect } from "@/components/Common/FilterSelect"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { Measurements } from "./Measurements"
import { MetrologyFilters } from "./MetrologyFilters"
import type { PartSearch } from "./measurementSelection"
import {
  PartReadButton,
  PartReadStatus,
  usePartReading,
} from "./PartReadStatus"
import type { Study } from "./types"

export function MetrologyPage({
  partId,
  search,
  embedded = false,
}: {
  partId?: string
  search: PartSearch
  embedded?: boolean
}) {
  const navigate = useNavigate()
  const reading = usePartReading(embedded ? undefined : partId)
  // The piece shows all its cotas; catalogue filters no longer scope this page.
  const consultationSearch = embedded
    ? { ...search, feature: undefined, category: undefined, tag: undefined }
    : search
  const options = useQuery({
    queryKey: ["metrology-filters"],
    queryFn: () => EvidenceService.readMetrologyFilters(),
    enabled: !embedded,
  })
  const result = useQuery({
    queryKey: ["part-evidence", partId, search.revision, search.snapshot],
    queryFn: () =>
      EvidenceService.readPartEvidence({
        partId: partId!,
        revision: search.revision,
        snapshotId: search.snapshot,
      }),
    enabled: Boolean(partId),
    refetchInterval: (q) =>
      ["queued", "processing"].includes(q.state.data?.study.state ?? "") ||
      ["queued", "processing"].includes(q.state.data?.refresh_job?.state ?? "")
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
        search: { ...values, editar: search.editar },
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
    visit(partId, { ...consultationSearch, ...values }, replace)
  const data = result.data
  const study =
    data?.study.state === "ready" ? (data.study.payload as Study) : undefined
  const drawing =
    data?.documents.find(
      (document) =>
        document.id === search.drawingFile &&
        document.filename.toLowerCase().endsWith(".pdf"),
    ) ??
    data?.documents.find((document) => document.id === data.drawing_file_id) ??
    (data?.drawing_reference_set
      ? undefined
      : data?.documents.find((document) =>
          /(?:DRW|plano|drawing).*\.pdf$/i.test(document.filename),
        ))
  const filters = (
    <div className="space-y-3">
      {!embedded && (
        <MetrologyFilters
          hidePart={embedded}
          options={options.data}
          partId={partId}
          part={
            data?.part ?? options.data?.parts.find((part) => part.id === partId)
          }
          search={search}
          onPart={(id) => {
            visit(id, {
              feature: search.feature,
              category: search.category,
              tag: search.tag,
            })
          }}
          onScope={(values) => {
            visit(partId, {
              revision: search.revision,
              snapshot: search.snapshot,
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
      )}
      {(data?.measurement_revisions?.length ?? 0) > 1 && (
        <div className="max-w-56">
          <FilterSelect
            label="Revisión de mediciones"
            value={search.revision ?? study?.measurement_revision ?? ""}
            options={(data?.measurement_revisions ?? []).map((revision) => ({
              value: revision,
              label: revision,
            }))}
            onChange={(revision) =>
              change({
                revision,
                snapshot: undefined,
                cota: undefined,
                q: undefined,
                element: undefined,
                height: undefined,
                evaluation: undefined,
                interval: undefined,
              })
            }
          />
        </div>
      )}
      {search.snapshot && (
        <p className="text-sm text-muted-foreground">
          Consulta de una importación anterior.
        </p>
      )}
    </div>
  )
  const error = (!embedded && options.error) || (partId ? result.error : null)
  const status =
    partId && result.isPending
      ? "Cargando cotas…"
      : ["queued", "processing"].includes(data?.study.state ?? "")
        ? "Preparando mediciones…"
        : data?.study.state === "error"
          ? data.study.message
          : undefined
  if (search.plano && drawing && partId)
    return (
      <Navigate
        to="/parts/$partId/fichero/$fileId"
        params={{ partId, fileId: drawing.id }}
        search={{
          ...search,
          plano: undefined,
          drawingQ: search.drawingQ ?? search.cota,
        }}
        replace
      />
    )
  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Metrología</h1>
          <div className="flex flex-wrap gap-2">
            {data?.part && (
              <PartReadButton
                reading={reading}
                folder={data.part.folder_path}
                editing={false}
              />
            )}
            <Button onClick={() => void navigate({ to: "/parts/nueva" })}>
              <Plus />
              Nueva pieza
            </Button>
          </div>
        </div>
      )}
      {!embedded && data?.part && <PartReadStatus reading={reading} />}
      {data?.refresh_job?.state === "error" && (
        <p role="alert" className="text-sm text-destructive">
          {data.refresh_job.message}
        </p>
      )}
      {error && <p role="alert">{fileErrorMessage(error)}</p>}
      <Measurements
        study={study}
        characteristics={data?.characteristics ?? []}
        features={data?.features ?? []}
        status={status}
        filters={
          !embedded ||
          (data?.measurement_revisions?.length ?? 0) > 1 ||
          search.snapshot
            ? filters
            : undefined
        }
        partSelected={Boolean(partId)}
        search={
          embedded
            ? consultationSearch
            : partId
              ? search
              : {
                  feature: search.feature,
                  category: search.category,
                  tag: search.tag,
                }
        }
        onChange={change}
        onDrawing={
          drawing && partId
            ? (code) =>
                void navigate({
                  to: "/parts/$partId/fichero/$fileId",
                  params: { partId, fileId: drawing.id },
                  search: {
                    ...consultationSearch,
                    plano: undefined,
                    drawingQ: code,
                  },
                })
            : undefined
        }
      />
    </div>
  )
}
