import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { EvidenceService, type PartPublic, PartsService } from "@/client"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"

export function PartDataImports() {
  const parts = useQuery({
    queryKey: ["parts", "catalog"],
    queryFn: () => PartsService.readParts({ limit: 1000 }),
  })
  const supported =
    parts.data?.data.filter(
      (part) =>
        part.code === "3212" && part.folder_path === "3212 Pump Housing",
    ) ?? []
  return (
    <section aria-label="Datos de piezas" className="space-y-4 border-t pt-6">
      <div>
        <h2 className="text-lg font-semibold">Datos de piezas</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Importa los archivos de mediciones y correcciones. Si no han cambiado,
          se conserva la importación actual.
        </p>
      </div>
      {parts.isPending ? (
        <p className="text-sm text-muted-foreground">Cargando piezas…</p>
      ) : parts.error ? (
        <p role="alert">{fileErrorMessage(parts.error)}</p>
      ) : supported.length ? (
        supported.map((part) => <PartImport key={part.id} part={part} />)
      ) : (
        <p className="text-sm text-muted-foreground">
          No hay piezas con una importación configurada.
        </p>
      )}
    </section>
  )
}

function PartImport({ part }: { part: PartPublic }) {
  const client = useQueryClient()
  const key = ["part-evidence", part.id]
  const evidence = useQuery({
    queryKey: key,
    queryFn: () => EvidenceService.readPartEvidence({ partId: part.id }),
    refetchInterval: (query) =>
      ["queued", "processing"].includes(query.state.data?.study.state ?? "")
        ? 2500
        : false,
  })
  const ingest = useMutation({
    mutationFn: () => EvidenceService.importPartEvidence({ partId: part.id }),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  })
  const state = evidence.data?.study.state
  const busy =
    ingest.isPending || ["queued", "processing"].includes(state ?? "")
  return (
    <div className="space-y-2 rounded-lg border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm font-medium">
          {part.code} · {part.name}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy || !evidence.data?.import_available}
          onClick={() => ingest.mutate()}
        >
          <RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`} />
          {busy
            ? "Procesando…"
            : state === "ready"
              ? "Reimportar archivos"
              : "Importar archivos"}
        </Button>
      </div>
      {(evidence.error || ingest.error) && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(evidence.error || ingest.error)}
        </p>
      )}
      {state === "error" && (
        <p role="alert" className="text-sm text-destructive">
          {evidence.data?.study.message}
        </p>
      )}
      {ingest.isSuccess && state === "ready" && (
        <output className="block text-sm text-muted-foreground">
          Datos disponibles para consultar.
        </output>
      )}
    </div>
  )
}
