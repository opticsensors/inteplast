import { Box, Maximize2, X } from "lucide-react"
import { lazy, Suspense, useState } from "react"

import type { FeaturePublic } from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { coverAsset } from "./cadCover"
import { FeatureThumbnail } from "./FeatureCard"

const StepCoverCanvas = lazy(() => import("./StepCoverCanvas"))

export function FeatureCover({ feature }: { feature: FeaturePublic }) {
  const [active, setActive] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const cover = feature.cover_3d
  const asset = cover ? coverAsset(feature, cover) : undefined
  const thumbnail = (
    <FeatureThumbnail
      feature={feature}
      fit="contain"
      className="size-32 sm:size-48"
    />
  )
  if (!cover)
    return feature.image ? (
      <FileLink
        fileId={feature.image.id}
        target="_blank"
        rel="noopener noreferrer"
        className="shrink-0"
      >
        {thumbnail}
      </FileLink>
    ) : (
      thumbnail
    )
  const model = (large = false) =>
    asset?.file ? (
      <Suspense
        fallback={<output className="p-4 text-sm">Cargando 3D…</output>}
      >
        <StepCoverCanvas
          file={asset.file}
          initial={cover}
          className={
            large ? "mx-auto max-w-[min(70vh,720px)]" : "size-32 sm:size-48"
          }
        />
      </Suspense>
    ) : (
      <p role="alert" className="p-3 text-xs">
        El CAD vinculado ha cambiado o ya no está disponible. Revisa la portada
        desde Editar.
      </p>
    )
  return (
    <div className="w-32 shrink-0 space-y-1 sm:w-48">
      {active && !expanded ? model() : thumbnail}
      <div className="flex justify-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setActive(!active)}
        >
          <Box className="size-3.5" />
          {active ? "Ver imagen" : "Activar 3D"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-8"
          title="Ampliar portada 3D"
          aria-label="Ampliar portada 3D"
          onClick={() => setExpanded(true)}
        >
          <Maximize2 className="size-3.5" />
        </Button>
      </div>
      <Dialog open={expanded} onOpenChange={setExpanded}>
        {expanded && (
          <DialogContent className="max-h-[95dvh] overflow-y-auto sm:max-w-4xl">
            <DialogHeader>
              <DialogTitle>{feature.name}</DialogTitle>
              <DialogDescription>
                Portada 3D con las superficies marcadas.
              </DialogDescription>
            </DialogHeader>
            {model(true)}
            <Button
              type="button"
              variant="outline"
              className="justify-self-end"
              onClick={() => setExpanded(false)}
            >
              <X className="size-4" />
              Cerrar
            </Button>
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}
