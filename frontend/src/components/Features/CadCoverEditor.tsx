import { Loader2 } from "lucide-react"
import { lazy, Suspense, useRef, useState } from "react"

import {
  type FeatureCover3D,
  type FeaturePublic,
  type FilePublic,
  FilesService,
} from "@/client"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { COVER_EDITOR_ROWS } from "./CoverDialog"
import { CoverLoading } from "./CoverLoading"
import { type CoverControls, coverAssets } from "./cadCover"
import { FeatureThumbnail } from "./FeatureCard"
import { usePendingTask } from "./usePendingTask"

const StepCoverCanvas = lazy(() => import("./StepCoverCanvas"))

export function CadCoverEditor({
  feature,
  initial,
  image,
  setBusy,
  onSaved,
  close,
}: {
  feature?: FeaturePublic
  image: FilePublic | null
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

  const preview =
    image && initial?.asset_id === asset?.id ? (
      <FeatureThumbnail
        feature={{ image, name: feature?.name ?? "Portada" }}
        fit="contain"
        className="size-full"
      />
    ) : (
      <div className="size-full rounded-lg border bg-muted" />
    )

  return (
    <div className={COVER_EDITOR_ROWS}>
      <select
        aria-label="Pieza CAD para la portada"
        className="h-9 w-full min-w-0 rounded-md border bg-background px-2 text-sm"
        value={asset?.id ?? ""}
        disabled={save.pending || !assets.length}
        onChange={(event) => {
          setAssetId(event.target.value)
          setUseSaved(true)
          setError("")
          setReady(false)
          setCount(0)
        }}
      >
        {!asset && (
          <option value="">
            {assets.length ? "Selecciona el CAD vinculado" : "Sin piezas CAD"}
          </option>
        )}
        {assets.map((item) => (
          <option key={item.id} value={item.id}>
            {item.part?.code} · {item.name}
          </option>
        ))}
      </select>
      <div
        data-slot="cover-surface"
        className={
          save.pending
            ? "relative size-full pointer-events-none"
            : "relative size-full"
        }
      >
        {asset?.file ? (
          <Suspense
            fallback={
              <>
                {preview}
                <CoverLoading />
              </>
            }
          >
            <StepCoverCanvas
              key={`${asset.id}:${useSaved}`}
              file={asset.file}
              initial={saved}
              editable
              disabled={save.pending}
              fallback={
                image && initial?.asset_id === asset.id ? preview : undefined
              }
              className="size-full"
              onReady={(api) => {
                controls.current = api
                setReady(Boolean(api))
              }}
              onSelectionChange={setCount}
              onResetSelection={() => {
                setUseSaved(false)
                setReady(false)
                setCount(0)
                setError("")
              }}
            />
          </Suspense>
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-3 rounded-lg border bg-muted p-4 text-center">
            <p role="alert" className="text-sm">
              {assets.length
                ? "Selecciona una pieza CAD."
                : feature
                  ? "Primero sube o vincula un STEP de tipo Pieza CAD en Piezas ejemplo."
                  : "Guarda primero el feature y añade el STEP de la pieza en Piezas ejemplo."}
            </p>
            {feature && !assets.length && (
              <Button
                type="button"
                variant="outline"
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
        )}
        {error && (
          <p
            role="alert"
            className="absolute inset-x-2 bottom-2 bg-background/95 p-2 text-sm text-destructive"
          >
            {error}
          </p>
        )}
      </div>
      <div className="flex justify-end gap-2">
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
          {save.pending && <Loader2 className="size-4 animate-spin" />}Aplicar
        </Button>
      </div>
    </div>
  )
}
