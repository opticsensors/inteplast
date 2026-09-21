import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { FileSearch, Plus, Ruler, Trash2 } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  type CharacteristicPublic,
  EvidenceService,
  type FeatureEvidencePublic,
  type FeaturePublic,
} from "@/client"
import { normalizeCota } from "@/components/Features/drawingSearchHelpers"
import { SaveStatus } from "@/components/Features/SaveStatus"
import { useAutosave } from "@/components/Features/useAutosave"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"

type AddedCota = { key: string; characteristic?: CharacteristicPublic }
const validCode = (code: string) =>
  /^N\d{1,6}(?:\.\d{1,3})?$/.test(normalizeCota(code))
const uniqueRevision = (items: CharacteristicPublic[]) => {
  const revisions = [
    ...new Set(items.map((item) => item.revision).filter(Boolean)),
  ]
  return revisions.length === 1 ? revisions[0] : undefined
}

export function FeaturePartEvidence({
  feature,
  partId,
  editable,
}: {
  feature: FeaturePublic
  partId: string
  editable?: boolean
}) {
  const client = useQueryClient()
  const [added, setAdded] = useState<AddedCota[]>([])
  const queryKey = ["feature-evidence", feature.id, partId]
  const result = useQuery({
    queryKey,
    queryFn: () =>
      EvidenceService.readFeatureEvidence({ featureId: feature.id, partId }),
  })
  const invalidate = () => {
    void client.invalidateQueries({ queryKey })
    void client.invalidateQueries({ queryKey: ["part-evidence", partId] })
    void client.invalidateQueries({ queryKey: ["features"] })
  }
  const assign = async (key: string, value: string) => {
    const code = normalizeCota(value)
    const linked =
      client.getQueryData<FeatureEvidencePublic>(queryKey)?.characteristics ??
      []
    let characteristic = linked.find((item) => item.code === code)
    if (!characteristic) {
      const evidence = await client.fetchQuery({
        queryKey: ["part-evidence", partId],
        queryFn: () => EvidenceService.readPartEvidence({ partId }),
        staleTime: 60_000,
      })
      const studyRevision = evidence.study.payload?.measurement_revision
      const revision =
        (typeof studyRevision === "string" && studyRevision.trim()) ||
        uniqueRevision(
          evidence.characteristics.filter((item) => item.code === code),
        ) ||
        uniqueRevision(evidence.characteristics) ||
        uniqueRevision(linked) ||
        "sin confirmar"
      characteristic = await EvidenceService.assignCharacteristic({
        featureId: feature.id,
        partId,
        requestBody: { code, revision, role: "primary" },
      })
    }
    const saved = characteristic
    const existing = client
      .getQueryData<FeatureEvidencePublic>(queryKey)
      ?.characteristics.some((item) => item.id === saved.id)
    client.setQueryData<FeatureEvidencePublic>(
      queryKey,
      (data) =>
        data && {
          ...data,
          characteristics: [
            ...data.characteristics.filter((item) => item.id !== saved.id),
            saved,
          ],
        },
    )
    // Keep new fields at the right-hand end instead of jumping to the API's alphabetical order.
    setAdded((items) =>
      existing
        ? items.filter((item) => item.key !== key)
        : items.map((item) =>
            item.key === key ? { ...item, characteristic: saved } : item,
          ),
    )
    invalidate()
  }
  const remove = useMutation({
    mutationFn: (characteristicId: string) =>
      EvidenceService.unassignCharacteristic({
        featureId: feature.id,
        characteristicId,
      }),
    onSuccess: (_, id) => {
      client.setQueryData<FeatureEvidencePublic>(
        queryKey,
        (data) =>
          data && {
            ...data,
            characteristics: data.characteristics.filter(
              (item) => item.id !== id,
            ),
          },
      )
      setAdded((items) =>
        items.filter((item) => item.characteristic?.id !== id),
      )
      invalidate()
    },
  })
  const drawing = feature.assets?.find(
    (asset) =>
      asset.part?.id === partId &&
      asset.kind === "drawing" &&
      asset.file?.filename.toLowerCase().endsWith(".pdf"),
  )
  const chip = (cota: CharacteristicPublic) => (
    <div
      key={cota.id}
      className="inline-flex h-7 shrink-0 items-center rounded-md border text-sm"
    >
      <Link
        to="/parts/$partId"
        params={{ partId }}
        search={{
          cota: cota.code,
          revision: cota.revision,
          feature: feature.id,
        }}
        className="px-2 font-medium hover:underline"
      >
        {cota.code}
      </Link>
      {drawing && (
        <Button asChild variant="ghost" size="icon" className="size-6 shrink-0">
          <Link
            to="/parts/$partId"
            params={{ partId }}
            search={{
              cota: cota.code,
              revision: cota.revision,
              feature: feature.id,
              plano: true,
              drawingQ: cota.code,
              drawingFile: drawing.file?.id,
            }}
            title={`Buscar ${cota.code} en el plano`}
          >
            <FileSearch className="size-3.5" />
            <span className="sr-only">Buscar {cota.code} en el plano</span>
          </Link>
        </Button>
      )}
      {editable && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-6 shrink-0 text-destructive"
          disabled={remove.isPending}
          onClick={() => remove.mutate(cota.id)}
        >
          <Trash2 className="size-3.5" />
          <span className="sr-only">Quitar {cota.code}</span>
        </Button>
      )}
    </div>
  )
  const additions = new Set(added.map((item) => item.characteristic?.id))
  const stored =
    result.data?.characteristics.filter((item) => !additions.has(item.id)) ?? []
  return (
    <section aria-label="Cotas" className="rounded-md border">
      <div
        className={cn(
          "flex items-start gap-2 text-sm",
          editable ? "px-1 py-1" : "px-2 py-1.5",
        )}
      >
        <div className="flex h-7 shrink-0 items-center gap-2">
          <Ruler className="size-4 shrink-0 text-muted-foreground" />
          <span className="w-16 shrink-0 text-xs uppercase tracking-wide text-muted-foreground">
            Cotas
          </span>
        </div>
        <div className="flex min-w-0 flex-1 flex-wrap items-start gap-2">
          {stored.map(chip)}
          {added.map((item) =>
            item.characteristic ? (
              chip(item.characteristic)
            ) : (
              <NewCota
                key={item.key}
                onSave={(code) => assign(item.key, code)}
                onCancel={() =>
                  setAdded((items) =>
                    items.filter((entry) => entry.key !== item.key),
                  )
                }
              />
            ),
          )}
          {result.isPending && (
            <span className="leading-7 text-xs text-muted-foreground">
              Cargando cotas…
            </span>
          )}
          {!editable &&
            !result.isPending &&
            !stored.length &&
            !added.length && (
              <span className="leading-7 text-xs italic text-muted-foreground">
                Sin cotas vinculadas
              </span>
            )}
          {editable && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7"
              disabled={!result.data || result.isError}
              onClick={() =>
                setAdded((items) => [...items, { key: crypto.randomUUID() }])
              }
            >
              <Plus className="mr-1 size-3.5" />
              Añadir cota
            </Button>
          )}
        </div>
      </div>
      {(result.error || remove.error) && (
        <p className="px-2 pb-1 text-xs text-destructive" role="alert">
          {fileErrorMessage(result.error || remove.error)}
        </p>
      )}
    </section>
  )
}

function NewCota({
  onSave,
  onCancel,
}: {
  onSave: (code: string) => Promise<void>
  onCancel: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const server = useMemo(() => ({ code: "" }), [])
  // Creating a link waits for blur/Enter (or the feature's Guardar), so a typing pause
  // at N1 cannot save the wrong cota while the user is entering N170.
  const save = useAutosave(
    server,
    (patch) => onSave(patch.code!),
    (values) => validCode(values.code),
    null,
  )
  useEffect(() => {
    input.current?.focus()
  }, [])
  return (
    <div className="flex max-w-full flex-col">
      <div className="inline-flex h-7 items-center rounded-md border">
        <Input
          ref={input}
          aria-label="Nueva cota"
          aria-invalid={save.error || undefined}
          placeholder="N170"
          value={save.values.code}
          disabled={save.saving}
          className="h-6 w-20 border-0 px-2 shadow-none focus-visible:ring-1"
          onChange={(event) => save.change({ code: event.target.value })}
          onBlur={(event) => {
            if (
              event.currentTarget.parentElement?.contains(event.relatedTarget)
            )
              return
            if (save.values.code.trim()) void save.flush()
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault()
              void save.flush()
            }
            if (event.key === "Escape") {
              event.preventDefault()
              onCancel()
            }
          }}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-6 shrink-0 text-destructive"
          disabled={save.saving}
          onPointerDown={(event) => event.preventDefault()}
          onClick={onCancel}
        >
          <Trash2 className="size-3.5" />
          <span className="sr-only">Quitar nueva cota</span>
        </Button>
      </div>
      <SaveStatus error={save.error} saving={save.saving} retry={save.flush} />
    </div>
  )
}
