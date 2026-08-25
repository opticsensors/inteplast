import { ImageIcon, Package2 } from "lucide-react"
import {
  type CSSProperties,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react"

import type { FeaturePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { fileUrl } from "@/utils"
import { CATEGORY_LABELS } from "./constants"
import { featureParts, partLabel } from "./parts"

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
    <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-muted-foreground">
      <Package2 className="size-3.5 shrink-0" />
      <span>
        {parts.length} pieza{parts.length === 1 ? "" : "s"}
      </span>
      <span aria-hidden>·</span>
      {shown.map((part, index) => (
        <span key={part.id} className="font-mono" title={partLabel(part)}>
          {part.code}
          {index < shown.length - 1 || rest > 0 ? "," : ""}
        </span>
      ))}
      {rest > 0 && <span>+{rest} mas</span>}
    </div>
  )
}

export function FeatureThumbnail({
  feature,
  className,
  style,
  fit = "cover",
}: {
  feature: FeaturePublic
  className?: string
  style?: CSSProperties
  /** En la tarjeta se recorta para que cuadre; en la ficha, no: la geometria
   *  es lo que se va a mirar y cortarla por los bordes seria absurdo. */
  fit?: "cover" | "contain"
}) {
  return (
    <div
      className={cn(
        "flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted",
        className,
      )}
      style={style}
    >
      {feature.image ? (
        <img
          src={fileUrl(feature.image.id)}
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

/** Lado minimo y maximo de la miniatura de la tarjeta, en px. */
const THUMB_MIN = 64
const THUMB_MAX = 144

/**
 * Mide el bloque de texto para que la miniatura sea cuadrada y tan alta como la
 * fila. Con CSS no sale: el alto de la fila lo marca el texto, y `aspect-ratio`
 * necesita un alto definido para deducir el ancho (comprobado en Chromium: sale
 * un rectangulo, no un cuadrado). Converge en dos pasadas porque el texto solo
 * puede crecer al estrecharse la columna, nunca encogerse.
 */
function useTextHeight() {
  const ref = useRef<HTMLDivElement>(null)
  const [height, setHeight] = useState<number>()

  useEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const measured = Math.round(entry.contentRect.height)
      setHeight(Math.min(Math.max(measured, THUMB_MIN), THUMB_MAX))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return { ref, height }
}

interface FeatureCardProps {
  feature: FeaturePublic
  onSelect?: (feature: FeaturePublic) => void
  /** Botones de Editar y Borrar de la pagina de gestion. */
  actions?: ReactNode
}

/** Tarjeta de resultado: imagen, nombre, descripcion, tags y piezas. */
export function FeatureCard({ feature, onSelect, actions }: FeatureCardProps) {
  const tags = feature.tags ?? []
  const { ref: textRef, height: thumbSide } = useTextHeight()

  return (
    <div
      className={cn(
        "relative flex gap-3 rounded-lg border p-3 transition-colors",
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
        style={thumbSide ? { width: thumbSide, height: thumbSide } : undefined}
      />
      <div ref={textRef} className="min-w-0 flex-1 space-y-1.5">
        <div className="flex items-start gap-2">
          <h3 className="flex-1 font-semibold leading-tight">{feature.name}</h3>
          {actions && <div className="relative z-20">{actions}</div>}
        </div>
        {feature.description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">
            {feature.description}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-1">
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
