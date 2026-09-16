import { Box, Eraser, Loader2 } from "lucide-react"
import { lazy, Suspense, useRef, useState } from "react"

import {
  type FeatureCover3D,
  type FeaturePublic,
  type FilePublic,
  FilesService,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { type CoverControls, coverAssets } from "./cadCover"
import { usePendingTask } from "./usePendingTask"

const StepCoverCanvas = lazy(() => import("./StepCoverCanvas"))

export function CadCoverEditor({
  feature,
  cover,
  onChange,
}: {
  feature?: FeaturePublic
  cover: FeatureCover3D | null
  onChange: (image: FilePublic, annotation: FeatureCover3D) => void
}) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) setOpen(next)
      }}
    >
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="w-full px-2 text-xs sm:text-sm"
        onClick={() => setOpen(true)}
      >
        <Box className="size-4" />
        {cover ? "Editar portada 3D" : "Desde CAD"}
      </Button>
      {open && (
        <DialogContent
          className="max-h-[95dvh] overflow-y-auto sm:max-w-3xl"
          showCloseButton={!busy}
          onPointerDownOutside={(event) => event.preventDefault()}
          onEscapeKeyDown={(event) => {
            if (busy) event.preventDefault()
          }}
        >
          <DialogHeader>
            <DialogTitle>Portada desde la pieza CAD</DialogTitle>
            <DialogDescription>
              Haz clic para marcar superficies en rojo. Arrastra para girar y
              usa la rueda para acercarte.
            </DialogDescription>
          </DialogHeader>
          <CoverEditorContent
            feature={feature}
            initial={cover}
            setBusy={setBusy}
            onSaved={(image, annotation) => {
              onChange(image, annotation)
              setOpen(false)
            }}
            close={() => setOpen(false)}
          />
        </DialogContent>
      )}
    </Dialog>
  )
}

function CoverEditorContent({
  feature,
  initial,
  setBusy,
  onSaved,
  close,
}: {
  feature?: FeaturePublic
  initial: FeatureCover3D | null
  setBusy: (busy: boolean) => void
  onSaved: (image: FilePublic, cover: FeatureCover3D) => void
  close: () => void
}) {
  const assets = coverAssets(feature)
  const [assetId, setAssetId] = useState(
    initial?.asset_id ?? assets[0]?.id ?? "",
  )
  const [useSaved, setUseSaved] = useState(true)
  const [ready, setReady] = useState(false)
  const [count, setCount] = useState(0)
  const [error, setError] = useState("")
  const controls = useRef<CoverControls | null>(null)
  const asset = assets.find((item) => item.id === assetId)
  const saved = useSaved && initial?.asset_id === assetId ? initial : null
  const save = usePendingTask(async (_: undefined) => {
    if (!asset?.file || !asset.part || !controls.current)
      throw new Error("Selecciona una pieza CAD.")
    setBusy(true)
    setError("")
    try {
      const result = await controls.current.capture()
      const uploaded = await FilesService.uploadFile({
        formData: {
          file: new File([result.image], "portada-cad.png", {
            type: "image/png",
          }),
        },
      })
      onSaved(uploaded, {
        ...result.annotation,
        asset_id: asset.id,
        part_id: asset.part.id,
        file_id: asset.file.id,
        file_version: asset.file.version ?? null,
      })
    } catch (failure) {
      setError(fileErrorMessage(failure))
      throw failure
    } finally {
      setBusy(false)
    }
  })

  if (!assets.length)
    return (
      <div className="space-y-4">
        <p role="alert" className="text-sm">
          {feature
            ? "Primero sube o vincula un STEP de tipo Pieza CAD en Piezas ejemplo."
            : "Guarda primero el feature y añade el STEP de la pieza en Piezas ejemplo."}
        </p>
        {feature && (
          <Button
            type="button"
            onClick={() => {
              close()
              requestAnimationFrame(() =>
                document
                  .getElementById("example-parts-editor")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" }),
              )
            }}
          >
            Ir a Piezas ejemplo
          </Button>
        )}
      </div>
    )

  return (
    <div className="space-y-3">
      <label className="block space-y-1 text-sm">
        <span>Pieza CAD</span>
        <select
          aria-label="Pieza CAD para la portada"
          className="h-9 w-full rounded-md border bg-background px-2"
          value={asset?.id ?? ""}
          disabled={save.pending}
          onChange={(event) => {
            setAssetId(event.target.value)
            setUseSaved(true)
            setError("")
            setReady(false)
            setCount(0)
          }}
        >
          {!asset && <option value="">Selecciona el CAD vinculado</option>}
          {assets.map((item) => (
            <option key={item.id} value={item.id}>
              {item.part?.code} · {item.name}
            </option>
          ))}
        </select>
      </label>
      {asset?.file && (
        <div className={save.pending ? "pointer-events-none" : ""}>
          <Suspense fallback={<output>Cargando editor…</output>}>
            <StepCoverCanvas
              key={`${asset.id}:${useSaved}`}
              file={asset.file}
              initial={saved}
              editable
              className="mx-auto max-w-[min(58vh,600px)]"
              onReady={(api) => {
                controls.current = api
                setReady(Boolean(api))
              }}
              onSelectionChange={setCount}
            />
          </Suspense>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={!ready || !count || save.pending}
            onClick={() => controls.current?.clear()}
          >
            <Eraser className="size-4" />
            Limpiar selección
          </Button>
          {saved && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={save.pending}
              onClick={() => {
                setUseSaved(false)
                setReady(false)
                setCount(0)
              }}
            >
              Nueva selección
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={save.pending}
            onClick={close}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            disabled={!ready || !count || save.pending}
            onClick={() => void save.run(undefined)}
          >
            {save.pending && <Loader2 className="size-4 animate-spin" />}Usar
            como portada
          </Button>
        </div>
      </div>
    </div>
  )
}
