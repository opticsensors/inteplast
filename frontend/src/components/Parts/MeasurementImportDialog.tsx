import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import {
  EvidenceService,
  type MeasurementFilePreview,
  type MeasurementFileSelection,
  type MeasurementPreview,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { fileErrorMessage } from "@/hooks/useFileAccess"

type FileChoice = MeasurementFilePreview & { included: boolean }
const labels: Record<MeasurementFilePreview["status"], string> = {
  new: "Nuevo",
  new_sample: "Nuevo muestreo o cavidad",
  new_revision: "Nueva revisión",
  imported: "Ya incorporado",
  replacement: "Mediciones modificadas",
  needs_context: "Completa los datos",
  unsupported: "No compatible",
}
const selection = (file: FileChoice): MeasurementFileSelection => ({
  path: file.path,
  sha256: file.sha256,
  revision: file.revision,
  sample: file.sample,
  cavity: file.cavity,
  replace_existing: file.replace_existing,
})

export function MeasurementReview({
  partId,
  initialPreview,
  onBusyChange,
  onSaved,
}: {
  partId: string
  initialPreview: MeasurementPreview
  onBusyChange?: (busy: boolean) => void
  onSaved?: () => Promise<void>
}) {
  const client = useQueryClient()
  const [files, setFiles] = useState<FileChoice[]>(() =>
    initialPreview.files.map((file) => ({
      ...file,
      included: !["imported", "unsupported", "replacement"].includes(
        file.status,
      ),
    })),
  )
  const [dirty, setDirty] = useState(false)
  const [revision, setRevision] = useState("")
  const history = useQuery({
    queryKey: ["measurement-history", partId],
    queryFn: () => EvidenceService.measurementHistory({ partId }),
  })
  const preview = useMutation({
    mutationFn: (files: MeasurementFileSelection[]) =>
      EvidenceService.previewMeasurements({ partId, requestBody: { files } }),
    onSuccess: (data) => {
      setFiles((previous) =>
        data.files.map((file) => ({
          ...file,
          included:
            !["imported", "unsupported"].includes(file.status) &&
            (previous.find((old) => old.path === file.path)?.included ??
              !["imported", "unsupported", "replacement"].includes(
                file.status,
              )),
        })),
      )
      setDirty(false)
    },
  })
  const commit = useMutation({
    mutationFn: () =>
      EvidenceService.importMeasurements({
        partId,
        requestBody: {
          context_key: (preview.data ?? initialPreview).context_key,
          files: files.filter((file) => file.included).map(selection),
        },
      }),
    onSuccess: async () => {
      preview.mutate([])
      await Promise.all([
        client.invalidateQueries({ queryKey: ["part-evidence", partId] }),
        client.invalidateQueries({ queryKey: ["feature-evidence"] }),
        client.invalidateQueries({ queryKey: ["measurement-history", partId] }),
        client.invalidateQueries({ queryKey: ["features"] }),
        client.invalidateQueries({ queryKey: ["metrology-filters"] }),
      ])
      await onSaved?.()
    },
  })
  const change = (
    path: string,
    patch: Partial<FileChoice>,
    needsReview = true,
  ) => {
    setFiles((files) =>
      files.map((file) => (file.path === path ? { ...file, ...patch } : file)),
    )
    if (needsReview) setDirty(true)
    commit.reset()
  }
  const selected = files.filter((file) => file.included)
  const pending = preview.isPending || commit.isPending
  useEffect(() => {
    onBusyChange?.(pending)
    return () => onBusyChange?.(false)
  }, [pending, onBusyChange])
  const ready =
    selected.length > 0 &&
    selected.every(
      (file) =>
        !["unsupported", "needs_context"].includes(file.status) &&
        (file.status !== "replacement" || file.replace_existing),
    )
  return (
    <div className="space-y-3">
      {preview.isPending && (
        <output className="text-sm text-muted-foreground">Leyendo CSV…</output>
      )}
      {(preview.error || commit.error) && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(preview.error || commit.error)}
        </p>
      )}
      {(preview.data ?? initialPreview).notices?.map((notice) => (
        <p key={notice} className="text-sm text-muted-foreground">
          {notice}
        </p>
      ))}
      {files.some(
        (file) => file.status !== "unsupported" && !file.revision,
      ) && (
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={`import-revision-${partId}`} className="text-sm">
            Revisión para los archivos sin identificar
          </label>
          <Input
            id={`import-revision-${partId}`}
            className="h-8 w-24"
            value={revision}
            onChange={(event) => setRevision(event.target.value)}
            disabled={pending}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!revision.trim() || pending}
            onClick={() => {
              setFiles((files) =>
                files.map((file) =>
                  file.revision || file.status === "unsupported"
                    ? file
                    : { ...file, revision: revision.trim() },
                ),
              )
              setDirty(true)
              commit.reset()
            }}
          >
            Aplicar
          </Button>
        </div>
      )}
      <fieldset disabled={pending} className="min-w-0 space-y-2">
        {files
          .filter((file) => file.status !== "imported")
          .map((file) => (
            <div key={file.path} className="space-y-2 rounded-md border p-3">
              <div className="flex items-start gap-2">
                <Checkbox
                  aria-label={`Seleccionar ${file.path}`}
                  checked={file.included}
                  disabled={file.status === "unsupported"}
                  onCheckedChange={(included) =>
                    change(file.path, { included: included === true }, false)
                  }
                />
                <div className="min-w-0 flex-1">
                  <p className="break-all text-sm">{file.path}</p>
                  <p className="text-xs text-muted-foreground">
                    {labels[file.status]}
                    {file.rows
                      ? ` · ${file.cotas} ${file.cotas === 1 ? "cota" : "cotas"} · ${file.rows} ${file.rows === 1 ? "medición" : "mediciones"}`
                      : ""}
                  </p>
                </div>
              </div>
              {file.status !== "unsupported" && (
                <div className="grid grid-cols-3 gap-2">
                  {(
                    [
                      ["revision", "Revisión"],
                      ["sample", "Muestreo"],
                      ["cavity", "Cavidad"],
                    ] as const
                  ).map(([field, label]) => (
                    <label
                      key={field}
                      htmlFor={`${partId}-${encodeURIComponent(file.path)}-${field}`}
                      className="min-w-0 space-y-1 text-xs text-muted-foreground"
                    >
                      {label}
                      <Input
                        id={`${partId}-${encodeURIComponent(file.path)}-${field}`}
                        className="h-8"
                        aria-label={`${label} de ${file.path}`}
                        value={file[field] ?? ""}
                        onChange={(event) =>
                          change(file.path, { [field]: event.target.value })
                        }
                      />
                    </label>
                  ))}
                </div>
              )}
              {file.issues?.map((issue) => (
                <p key={issue} className="text-xs text-muted-foreground">
                  {issue}
                </p>
              ))}
              {file.status === "replacement" && (
                <label
                  htmlFor={`${partId}-${encodeURIComponent(file.path)}-replace`}
                  className="flex items-start gap-2 text-sm"
                >
                  <Checkbox
                    id={`${partId}-${encodeURIComponent(file.path)}-replace`}
                    checked={file.replace_existing}
                    onCheckedChange={(checked) =>
                      change(
                        file.path,
                        { replace_existing: checked === true },
                        false,
                      )
                    }
                  />
                  Usar estas mediciones conservando la versión anterior en el
                  historial.
                </label>
              )}
              {(file.examples?.length ?? 0) > 0 && (
                <details className="text-xs text-muted-foreground">
                  <summary className="cursor-pointer">
                    Comprobar valores de ejemplo
                  </summary>
                  <div className="mt-2 space-y-1">
                    {file.examples?.map((row, index) => (
                      <p key={`${file.path}-${index}`}>
                        {(row.numbers as string[]).join(" / ")} · Nominal{" "}
                        {String(row.nominal)} · Tol.{" "}
                        {String(row.tol_inf ?? "—")} /{" "}
                        {String(row.tol_sup ?? "—")} · Medido{" "}
                        {String(row.value)} {String(row.unit)}
                      </p>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
      </fieldset>
      {commit.data && (
        <output className="text-sm">
          Archivos incorporados: {commit.data.imported}. Ya importados:{" "}
          {commit.data.skipped}. Ya puedes seleccionar sus cotas en «Añadir
          cota».
        </output>
      )}
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={pending}
          onClick={() => {
            setFiles([])
            commit.reset()
            preview.mutate([])
          }}
        >
          Detectar de nuevo
        </Button>
        {dirty && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={pending || !selected.length}
            onClick={() => preview.mutate(selected.map(selection))}
          >
            Revisar selección
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          disabled={pending || dirty || !ready || Boolean(commit.data)}
          onClick={() => commit.mutate()}
        >
          {commit.isPending && <Loader2 className="size-4 animate-spin" />}{" "}
          Guardar datos revisados
        </Button>
      </div>
      {!!history.data?.length && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">
            Historial de importaciones ({history.data.length})
          </summary>
          <div className="mt-2 space-y-2">
            {history.data.map((item) => (
              <div
                key={item.id}
                className="flex flex-wrap justify-between gap-2 rounded-md border p-2"
              >
                <span>
                  Rev. {item.revision} ·{" "}
                  {item.baseline
                    ? "Datos previos a la importación CSV"
                    : `intern.${item.sample} · ${item.cavity.toUpperCase()}`}{" "}
                  · {new Date(item.imported_at).toLocaleString()} ·{" "}
                  {item.active ? "Vigente" : "Anterior"}
                </span>
                <Link
                  to="/parts/$partId"
                  params={{ partId }}
                  search={{ revision: item.revision, snapshot: item.id }}
                  className="text-muted-foreground underline"
                >
                  Consultar
                </Link>
              </div>
            ))}
          </div>
        </details>
      )}
      {history.error && (
        <p role="alert" className="text-sm text-destructive">
          No se pudo cargar el historial.
        </p>
      )}
    </div>
  )
}
