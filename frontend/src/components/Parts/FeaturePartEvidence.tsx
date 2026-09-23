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
import { SearchSelect } from "@/components/Common/SearchSelect"
import { normalizeCota } from "@/components/Features/drawingSearchHelpers"
import { SaveStatus } from "@/components/Features/SaveStatus"
import { useAutosave } from "@/components/Features/useAutosave"
import { usePendingTask } from "@/components/Features/usePendingTask"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { fileErrorMessage } from "@/hooks/useFileAccess"

type AddedCota = {
  key: string
  characteristic?: CharacteristicPublic
  manual?: boolean
}
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
  onSelectCota,
}: {
  feature: FeaturePublic
  partId: string
  editable?: boolean
  onSelectCota?: (cota: CharacteristicPublic) => void
}) {
  const client = useQueryClient()
  const [added, setAdded] = useState<AddedCota[]>([])
  const queryKey = ["feature-evidence", feature.id, partId]
  const result = useQuery({
    queryKey,
    queryFn: () =>
      EvidenceService.readFeatureEvidence({ featureId: feature.id, partId }),
  })
  const partEvidence = useQuery({
    queryKey: ["part-evidence", partId],
    queryFn: () => EvidenceService.readPartEvidence({ partId }),
    enabled: Boolean(editable),
  })
  const invalidate = () => {
    void client.invalidateQueries({ queryKey })
    void client.invalidateQueries({ queryKey: ["part-evidence", partId] })
    void client.invalidateQueries({ queryKey: ["features"] })
  }
  const assign = async (
    key: string,
    value: string,
    selectedRevision?: string,
  ) => {
    const code = normalizeCota(value)
    const linked =
      client.getQueryData<FeatureEvidencePublic>(queryKey)?.characteristics ??
      []
    let characteristic = linked.find(
      (item) =>
        item.code === code &&
        (!selectedRevision || item.revision === selectedRevision),
    )
    if (!characteristic) {
      const evidence = await client.fetchQuery({
        queryKey: ["part-evidence", partId],
        queryFn: () => EvidenceService.readPartEvidence({ partId }),
        staleTime: 0,
      })
      const studyRevision = evidence.study.payload?.measurement_revision
      const revision =
        selectedRevision ||
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
  )?.file
  const chip = (cota: CharacteristicPublic) => (
    <div
      key={cota.id}
      className="inline-flex h-7 shrink-0 items-center rounded-md border text-sm"
    >
      {onSelectCota ? (
        <button
          type="button"
          className="h-full rounded-md px-2 font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => onSelectCota(cota)}
        >
          {cota.code}
        </button>
      ) : (
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
      )}
      {drawing && (
        <Button asChild variant="ghost" size="icon" className="size-6 shrink-0">
          <Link
            to="/parts/$partId/fichero/$fileId"
            params={{ partId, fileId: drawing.id }}
            search={{
              cota: cota.code,
              revision: cota.revision,
              feature: feature.id,
              drawingQ: cota.code,
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
    <section aria-label="Cotas" className="space-y-2">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <Ruler className="size-4 shrink-0 text-muted-foreground" />
        Cotas
      </h3>
      <div className="text-sm">
        <div className="flex min-w-0 flex-1 flex-wrap items-start gap-1.5">
          {stored.map(chip)}
          {added.map((item) =>
            item.characteristic ? (
              chip(item.characteristic)
            ) : partEvidence.data?.measurement_revisions?.length &&
              partEvidence.data.characteristics.length &&
              !item.manual ? (
              <ImportedCota
                key={item.key}
                choices={partEvidence.data.characteristics}
                onSelect={(cota) => assign(item.key, cota.code, cota.revision)}
                onManual={() =>
                  setAdded((items) =>
                    items.map((entry) =>
                      entry.key === item.key
                        ? { ...entry, manual: true }
                        : entry,
                    ),
                  )
                }
                onCancel={() =>
                  setAdded((items) =>
                    items.filter((entry) => entry.key !== item.key),
                  )
                }
              />
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

function ImportedCota({
  choices,
  onSelect,
  onManual,
  onCancel,
}: {
  choices: CharacteristicPublic[]
  onSelect: (cota: CharacteristicPublic) => Promise<void>
  onManual: () => void
  onCancel: () => void
}) {
  const save = usePendingTask(onSelect)
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <div className="w-44">
          <SearchSelect
            label="Nueva cota"
            placeholder="Seleccionar cota"
            emptyLabel="Seleccionar cota"
            defaultOpen
            compact
            disabled={save.pending}
            options={[
              ...choices.map((cota) => ({
                value: cota.id,
                label: `${cota.code} · rev. ${cota.revision}`,
              })),
              { value: "manual", label: "Escribir otra cota" },
            ]}
            onChange={(id) => {
              const cota = choices.find((cota) => cota.id === id)
              if (cota) void save.run(cota)
              else if (id === "manual") onManual()
            }}
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-6 text-destructive"
          disabled={save.pending}
          onClick={onCancel}
        >
          <Trash2 className="size-3.5" />
          <span className="sr-only">Quitar nueva cota</span>
        </Button>
      </div>
      <SaveStatus error={save.error} saving={save.pending} retry={save.retry} />
    </div>
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
