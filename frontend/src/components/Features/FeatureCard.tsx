import { ImageIcon, Package2 } from "lucide-react"
import type { CSSProperties, ReactNode } from "react"

import type { FeaturePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { useFileAccess } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import { CATEGORY_LABELS } from "./constants"
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
  style,
  fit = "cover",
}: {
  feature: Pick<FeaturePublic, "image" | "name">
  className?: string
  style?: CSSProperties
  /** En la tarjeta se recorta para que cuadre; en la ficha, no: la geometria
   *  es lo que se va a mirar y cortarla por los bordes seria absurdo. */
  fit?: "cover" | "contain"
}) {
  const { url } = useFileAccess(feature.image?.id)
  return (
    <div
      className={cn(
        "flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted",
        className,
      )}
      style={style}
    >
      {feature.image &&
      url &&
      isPreviewableImage(feature.image.content_type) ? (
        <img
          src={url}
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

interface FeatureCardProps {
  feature: FeaturePublic
  onSelect?: (feature: FeaturePublic) => void
  /** Acciones independientes del boton que abre la ficha en lectura. */
  actions?: ReactNode
  showKind?: boolean
}

/** Tarjeta de resultado: imagen, nombre, descripcion, tags y piezas. */
export function FeatureCard({
  feature,
  onSelect,
  actions,
  showKind = false,
}: FeatureCardProps) {
  const tags = feature.tags ?? []

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
      <FeatureThumbnail
        feature={feature}
        className="size-24 self-center sm:size-36"
      />
      <div className="h-36 min-w-0 flex-1 space-y-1.5">
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
          {feature.category && (
            <Badge variant="secondary">
              {CATEGORY_LABELS[feature.category]}
            </Badge>
          )}
          {tags.map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>
        <PartSummary feature={feature} />
      </div>
    </div>
  )
}
