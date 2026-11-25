import { useQuery } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { Suspense, useRef, useState } from "react"

import {
  CatalogService,
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
import { StepCoverCanvas } from "./lazyStepCoverCanvas"
import { usePendingTask } from "./usePendingTask"

export function CadCoverEditor({
  feature,
  partId,
  initial,
  image,
  autoImage,
  setBusy,
  onSaved,
  close,
}: {
  feature?: FeaturePublic
  /** The piece is chosen by the carousel: only its STEP files are offered. */
  partId?: string
  image: FilePublic | null
  autoImage?: FilePublic | null
  initial: FeatureCover3D | null
  setBusy: (busy: boolean) => void
  onSaved: (image: FilePublic, cover: FeatureCover3D) => void
  close: () => void
}) {
  const assets = partId
    ? coverAssets(feature).filter((item) => item.part?.id === partId)
    : []
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
      throw new Error("Selecciona un CAD.")
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

  const ownPreview = asset && initial?.asset_id === asset.id ? image : null
  const detail = useQuery({
    queryKey: ["parts", "detail", partId],
    queryFn: () => CatalogService.readPartDetail({ partId: partId! }),
    enabled: Boolean(partId && asset?.file && autoImage && !ownPreview),
  })
  const piece = detail.data?.part
  const previewImage =
    ownPreview ??
    (piece?.cad && piece.cad.id === asset?.file?.id ? piece.image : null)
  const preview = previewImage ? (
    <FeatureThumbnail
      feature={{
        image: previewImage,
        name: feature?.name ?? "Portada de la pieza",
      }}
      fit="contain"
      className="size-full"
    />
  ) : (
    <div className="size-full rounded-lg border bg-muted" />
  )

  return (
    <div className={COVER_EDITOR_ROWS}>
      {assets.length > 1 ? (
        <select
          aria-label="CAD para la portada"
          className="h-9 w-full min-w-0 rounded-md border bg-background px-2 text-sm"
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
              {item.name}
            </option>
          ))}
        </select>
      ) : (
        <p
          className="flex min-w-0 items-center truncate text-sm text-muted-foreground"
          title={asset?.name}
        >
          {asset?.name}
        </p>
      )}
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
              color={feature?.color}
              editable
              allowWholeComponent={assets.length > 1}
              disabled={save.pending}
              fallback={previewImage ? preview : undefined}
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
                ? "Selecciona un CAD."
                : partId
                  ? "Vincula el CAD desde la ficha de la pieza."
                  : "Añade una pieza que tenga un CAD vinculado."}
            </p>
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
          disabled={!ready || (!count && assets.length < 2) || save.pending}
          onClick={() => void save.run(undefined)}
        >
          {save.pending && <Loader2 className="size-4 animate-spin" />}Aplicar
        </Button>
      </div>
    </div>
  )
}
