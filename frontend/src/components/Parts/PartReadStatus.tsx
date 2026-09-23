import {
  useIsMutating,
  useMutation,
  useMutationState,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { FileText, Loader2, RefreshCw } from "lucide-react"
import { useEffect, useRef } from "react"
import { PartsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { fileErrorMessage } from "@/hooks/useFileAccess"

export const PIECE_QUERY_KEYS = [
  "parts",
  "features",
  "part-evidence",
  "feature-evidence",
  "metrology-filters",
  "measurement-history",
]

export function useReadPartData() {
  const client = useQueryClient()
  return useMutation({
    mutationKey: ["read-piece"],
    mutationFn: (partId: string) => PartsService.readPartData({ partId }),
    onMutate: (partId: string) =>
      client.cancelQueries({ queryKey: ["piece-read-report", partId] }),
    onSuccess: async (report, partId) => {
      client.setQueryData(["piece-read-report", partId], report)
      await Promise.all(
        PIECE_QUERY_KEYS.map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      )
    },
  })
}

const STATUS: Record<string, string> = {
  imported: "Leído",
  unchanged: "Sin cambios",
  used: "Leído",
  queued: "Pendiente",
  processing: "Leyendo",
  error: "Error",
}

export function usePartReading(partId?: string) {
  const client = useQueryClient()
  const reading =
    useIsMutating({
      mutationKey: ["read-piece"],
      predicate: (mutation) =>
        Boolean(partId) && mutation.state.variables === partId,
    }) > 0
  const read = useReadPartData()
  const attempts = useMutationState({
    filters: {
      mutationKey: ["read-piece"],
      predicate: (mutation) =>
        Boolean(partId) && mutation.state.variables === partId,
    },
    select: (mutation) => ({
      error: mutation.state.error,
      submittedAt: mutation.state.submittedAt,
    }),
  })
  const latestAttempt = [...attempts].sort(
    (a, b) => b.submittedAt - a.submittedAt,
  )[0]
  const readError = latestAttempt?.error
  const report = useQuery({
    queryKey: ["piece-read-report", partId],
    queryFn: () => PartsService.readPartDataReport({ partId: partId! }),
    enabled: Boolean(partId) && !reading,
    refetchInterval: (query) =>
      query.state.data?.state === "processing" ? 2000 : false,
  })
  const previous = useRef<string | undefined>(undefined)
  useEffect(() => {
    if (
      previous.current === "processing" &&
      report.data?.state !== "processing"
    ) {
      for (const key of PIECE_QUERY_KEYS)
        void client.invalidateQueries({ queryKey: [key] })
    }
    previous.current = report.data?.state
  }, [report.data?.state, client])
  return {
    partId,
    reading,
    busy: reading || report.data?.state === "processing",
    data: report.data,
    error: readError ?? report.error,
    refresh: () => {
      if (partId) read.mutate(partId)
    },
  }
}

type PartReading = ReturnType<typeof usePartReading>

export function PartReadButton({
  reading,
  folder,
  editing,
}: {
  reading: PartReading
  folder?: string | null
  editing: boolean
}) {
  const disabled = reading.busy || editing || !folder || !reading.partId
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex shrink-0">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground"
            aria-label="Actualizar datos"
            disabled={disabled}
            onClick={reading.refresh}
          >
            {reading.busy ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-72" align="end">
        Lee la carpeta para extraer automáticamente las cotas, mediciones y
        correcciones compatibles.
        {!reading.partId ? (
          <p className="mt-1">Disponible al crear la pieza.</p>
        ) : editing ? (
          <p className="mt-1">Guarda los cambios antes de actualizar.</p>
        ) : !folder ? (
          <p className="mt-1">Vincula una carpeta desde Editar pieza.</p>
        ) : null}
      </TooltipContent>
    </Tooltip>
  )
}

export function PartReadStatus({
  reading: { busy, reading, data, error },
}: {
  reading: PartReading
}) {
  if (!busy && !data && !error) return null
  const label = busy
    ? "Lectura en curso"
    : error || data?.state === "error"
      ? "No se ha podido completar la lectura"
      : data?.state === "partial"
        ? "Lectura con incidencias"
        : "Lectura completada"
  return (
    <section
      className="mb-3 space-y-2 text-xs text-muted-foreground"
      aria-label="Lectura de datos"
    >
      {busy && (
        <output className="flex items-center gap-2" aria-live="polite">
          <Loader2 className="size-3.5 animate-spin" />
          {reading
            ? "Leyendo los datos de la carpeta…"
            : "Procesando las correcciones…"}
        </output>
      )}
      {error && (
        <p role="alert" className="text-destructive">
          {fileErrorMessage(error)}
        </p>
      )}
      {data && !reading && !error && (
        <details open={data.state === "error" || data.state === "partial"}>
          <summary className="cursor-pointer">
            <span>{label}</span>
            <span aria-hidden="true"> · </span>
            <span>Ficheros de la lectura ({data.files?.length ?? 0})</span>
          </summary>
          <div className="mt-2 space-y-2">
            {data.updated_at && (
              <p>{new Date(data.updated_at).toLocaleString("es-ES")}</p>
            )}
            <p>
              Grupos de mediciones incorporados: {data.imported ?? 0} · Sin
              cambios: {data.skipped ?? 0}
            </p>
            {data.notices?.map((notice) => (
              <p key={notice}>{notice}</p>
            ))}
            <ul className="space-y-1.5">
              {data.files?.map((file) => (
                <li
                  key={`${file.group}-${file.path}`}
                  className="flex min-w-0 items-center gap-2"
                >
                  <FileText className="size-3.5 shrink-0" />
                  <span className="min-w-0 flex-1 truncate" title={file.path}>
                    {file.path.split("/").pop()}
                  </span>
                  <span className="shrink-0">
                    {STATUS[file.status] ?? file.status}
                  </span>
                </li>
              ))}
            </ul>
            {!data.files?.length && (
              <p>No se ha utilizado ningún fichero para extraer datos.</p>
            )}
          </div>
        </details>
      )}
    </section>
  )
}
