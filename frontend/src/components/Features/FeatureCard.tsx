import { ImageIcon, Loader2, Package2 } from "lucide-react"
import { type ReactNode, type Ref, useState } from "react"

import type { FeaturePublic } from "@/client"
import { FeatureWarnings } from "@/components/Catalog/CatalogWarnings"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useFeaturePreview } from "@/hooks/useFeaturePreview"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import { CAD_COVER_BACKGROUND } from "./cadCover"
import { featureParts, partLabel } from "./parts"
import { isPreviewableImage } from "./viewers"

/** Cuantos codigos de pieza caben en la tarjeta antes de resumir. */
const MAX_CODES = 4

/**
 * En cuantas piezas aparece el feature. Antes aqui salia un badge por fichero
 * con su nombre y era ilegible: cuatro badges que ponian todos "3212 algo".
 */
function PartSummary({ feature }: { feature: FeaturePublic }) {
  const parts = featureParts(feature)
  if (parts.length === 0) return null

  const shown = parts.slice(0, MAX_CODES)
  const rest = parts.length - shown.length

  return (
    <div className="flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
      <Package2 className="size-3.5 shrink-0" />
      <span className="shrink-0">
        {parts.length} pieza{parts.length === 1 ? "" : "s"}
      </span>
      <span aria-hidden>·</span>
      <span className="truncate" title={parts.map(partLabel).join(", ")}>
        <span className="font-mono">
          {shown.map((part) => part.code).join(", ")}
        </span>
        {rest > 0 && <span>, +{rest} mas</span>}
      </span>
    </div>
  )
}

export function FeatureThumbnail({
  feature,
  className,
  cadBackground,
  fit = "cover",
  elementRef,
  coverError,
  retryCover,
  checking,
}: {
  feature: Pick<FeaturePublic, "image" | "name">
  className?: string
  cadBackground?: boolean
  elementRef?: Ref<HTMLDivElement>
  coverError?: unknown
  retryCover?: () => void
  checking?: boolean
  /** En la tarjeta se recorta para que cuadre; en la ficha, no: la geometria
   *  es lo que se va a mirar y cortarla por los bordes seria absurdo. */
  fit?: "cover" | "contain"
}) {
  const access = useFileAccess(feature.image?.id)
  const { url } = access
  const [failedUrl, setFailedUrl] = useState<string>()
  const failedImage =
    feature.image && (access.isError || (url && url === failedUrl))
  return (
    <div
      ref={elementRef}
      className={cn(
        "flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted",
        className,
      )}
      style={
        cadBackground ? { backgroundColor: CAD_COVER_BACKGROUND } : undefined
      }
    >
      {retryCover && (coverError || failedImage) ? (
        <div
          className="flex flex-col items-center gap-1 p-1 text-center text-xs"
          title={fileErrorMessage(coverError || access.error)}
        >
          <span>Portada no disponible</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="relative z-20"
            aria-label={`Reintentar portada de ${feature.name}`}
            disabled={checking || access.isFetching}
            onClick={() => {
              if (failedImage && !coverError) {
                setFailedUrl(undefined)
                void access.refetch()
              } else retryCover()
            }}
          >
            Reintentar
          </Button>
        </div>
      ) : checking && !feature.image ? (
        <Loader2
          aria-label="Comprobando portada"
          className="size-4 animate-spin text-muted-foreground"
        />
      ) : feature.image &&
        url &&
        isPreviewableImage(feature.image.content_type) ? (
        <img
          src={url}
          onError={retryCover ? () => setFailedUrl(url) : undefined}
          alt={feature.name}
          className={cn(
            "size-full",
            fit === "cover" ? "object-cover" : "object-contain",
          )}
        />
      ) : (
        <ImageIcon className="size-8 text-muted-foreground" />
      )}
    </div>
  )
}

/**
 * Cover of a catalogue card: the capture of the first piece. With two pieces or more,
 * two layers behind it and the number of pieces; navigation is on the feature page
 * (docs/plan-portadas-por-pieza-2026-11-18.md, decisions 2 and 5).
 */
export function FeatureCoverStack({
  feature,
  className,
  flatClassName,
}: {
  feature: FeaturePublic
  /** Size and placement, the same with or without layers. */
  className?: string
  /** Extra classes of the capture when it is shown alone. */
  flatClassName?: string
}) {
  const { ref, image, checking, error, retry } = useFeaturePreview({
    featureId: feature.id,
    markedPartId: feature.first_marked_part_id,
    deferredPartId: feature.deferred_cover_part_id,
    original: feature.cover_image,
  })
  const cover = { image, name: feature.name }
  const count = feature.part_count ?? 0
  if (count < 2)
    return (
      <FeatureThumbnail
        elementRef={ref}
        coverError={error}
        retryCover={retry}
        checking={checking}
        feature={cover}
        className={cn(className, flatClassName)}
      />
    )
  const surface = "border-neutral-600 bg-white"
  const layer = cn("absolute rounded-md border", surface)
  return (
    <div
      ref={ref}
      data-slot="cover-stack"
      className={cn("relative shrink-0 pr-2 pt-2", className)}
    >
      <div aria-hidden className={cn(layer, "bottom-2 left-2 right-0 top-0")} />
      <div aria-hidden className={cn(layer, "inset-1")} />
      <FeatureThumbnail
        feature={cover}
        coverError={error}
        retryCover={retry}
        checking={checking}
        className={cn("relative size-full [&>svg]:text-neutral-600", surface)}
      />
      <span
        className="absolute right-4 top-4 rounded-full bg-neutral-900/90 px-2 py-0.5 text-[11px] font-medium tabular-nums text-white"
        title={`${count} piezas`}
      >
        {count}
        <span className="sr-only"> piezas</span>
      </span>
    </div>
  )
}

interface FeatureCardProps {
  feature: FeaturePublic
  onSelect?: (feature: FeaturePublic) => void
  /** Acciones independientes del boton que abre la ficha en lectura. */
  actions?: ReactNode
  showKind?: boolean
}

/** Tarjeta de resultado: imagen, nombre, descripcion y piezas. */
export function FeatureCard({
  feature,
  onSelect,
  actions,
  showKind = false,
}: FeatureCardProps) {
  return (
    <div
      className={cn(
        "relative flex gap-3 rounded-lg border p-3 transition-colors",
        showKind && "border-l-4 border-l-primary/60",
        onSelect && "hover:border-primary/50 hover:bg-accent/50",
      )}
    >
      {/* Boton que cubre la tarjeta, para que los botones de accion puedan
          ser botones sin anidarlos dentro de este. */}
      {onSelect && (
        <button
          type="button"
          className="absolute inset-0 z-10 cursor-pointer rounded-lg"
          onClick={() => onSelect(feature)}
        >
          <span className="sr-only">Abrir {feature.name}</span>
        </button>
      )}
      <FeatureCoverStack
        feature={feature}
        className="size-24 self-center sm:size-36"
      />
      <div className="min-h-36 min-w-0 flex-1 space-y-1.5">
        <div className="flex items-start gap-2">
          <h3
            className="line-clamp-2 min-w-0 flex-1 break-words font-semibold leading-tight"
            title={feature.name}
          >
            {feature.name}
          </h3>
          {actions && <div className="relative z-20 shrink-0">{actions}</div>}
        </div>
        {feature.description && (
          <p className="line-clamp-2 break-words text-sm text-muted-foreground">
            {feature.description}
          </p>
        )}
        <div className="flex items-center gap-1 overflow-hidden">
          {showKind && (
            <Badge variant="outline" className="border-primary/40 text-primary">
              Feature
            </Badge>
          )}
        </div>
        <PartSummary feature={feature} />
        <FeatureWarnings feature={feature} />
      </div>
    </div>
  )
}
