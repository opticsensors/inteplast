import { lazy, Suspense, useState } from "react"

import type { FeaturePublic } from "@/client"
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { CoverButton } from "./CoverButton"
import { CoverDialog } from "./CoverDialog"
import { CoverLoading } from "./CoverLoading"
import { coverAsset } from "./cadCover"
import { FeatureThumbnail } from "./FeatureCard"

const StepCoverCanvas = lazy(() => import("./StepCoverCanvas"))

export function FeatureCover({ feature }: { feature: FeaturePublic }) {
  const [expanded, setExpanded] = useState(false)
  if (!feature.image && !feature.cover_3d)
    return <FeatureThumbnail feature={feature} className="size-32 sm:size-48" />

  return (
    <Dialog open={expanded} onOpenChange={setExpanded}>
      <DialogTrigger asChild>
        <CoverButton image={feature.image} name={feature.name} />
      </DialogTrigger>
      {expanded && <CoverViewer feature={feature} />}
    </Dialog>
  )
}

function CoverViewer({ feature }: { feature: FeaturePublic }) {
  const cover = feature.cover_3d
  const asset = cover ? coverAsset(feature, cover) : undefined
  const image = (
    <FeatureThumbnail feature={feature} fit="contain" className="size-full" />
  )

  return (
    <CoverDialog>
      <DialogHeader>
        <DialogTitle className="pr-6">{feature.name}</DialogTitle>
        <DialogDescription className="sr-only">
          {cover
            ? "Portada 3D de la pieza con las superficies marcadas."
            : "Imagen de portada ampliada."}
        </DialogDescription>
      </DialogHeader>
      <div
        data-slot="cover-surface"
        className="relative size-[var(--cover-size)]"
      >
        {!cover && image}
        {cover && (
          <div className="size-full">
            {asset?.file ? (
              <Suspense
                fallback={
                  <>
                    {image}
                    <CoverLoading />
                  </>
                }
              >
                <StepCoverCanvas
                  file={asset.file}
                  initial={cover}
                  fallback={image}
                  className="size-full"
                />
              </Suspense>
            ) : (
              <div className="relative size-full">
                {image}
                <p
                  role="alert"
                  className="absolute inset-x-2 bottom-2 rounded bg-background/95 p-3 text-sm"
                >
                  El CAD vinculado ha cambiado o ya no está disponible. Revisa
                  la portada desde Editar.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </CoverDialog>
  )
}
