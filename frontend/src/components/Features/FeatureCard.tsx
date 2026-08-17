import { Box, FileText, ImageIcon, Package } from "lucide-react"
import {
  type CSSProperties,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react"

import type { AssetKind, FeaturePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { fileUrl } from "@/utils"
import { ASSET_KIND_LABELS, CATEGORY_LABELS } from "./constants"

export const ASSET_ICONS: Record<AssetKind, typeof Box> = {
  mold: Box,
  part: Package,
  drawing: FileText,
}

const ASSET_BADGE_STYLES: Record<AssetKind, string> = {
  mold: "border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
  part: "border-sky-500/40 text-sky-600 dark:text-sky-400",
  drawing: "border-red-500/40 text-red-600 dark:text-red-400",
}

export function AssetBadge({ kind, name }: { kind: AssetKind; name: string }) {
  const Icon = ASSET_ICONS[kind]
  return (
    <Badge
      variant="outline"
      className={cn("gap-1 rounded-md", ASSET_BADGE_STYLES[kind])}
      title={ASSET_KIND_LABELS[kind]}
    >
      <Icon className="size-3" />
      <span className="max-w-40 truncate">{name}</span>
    </Badge>
  )
}

export function FeatureThumbnail({
  feature,
  className,
  style,
}: {
  feature: FeaturePublic
  className?: string
  style?: CSSProperties
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
          className="size-full object-cover"
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
  /** Menu de acciones de la pagina de gestion. */
  actions?: ReactNode
}

/** Tarjeta de resultado: imagen, nombre, descripcion, tags y adjuntos. */
export function FeatureCard({ feature, onSelect, actions }: FeatureCardProps) {
  const assets = feature.assets ?? []
  const tags = feature.tags ?? []
  const { ref: textRef, height: thumbSide } = useTextHeight()

  return (
    <div
      className={cn(
        "relative flex gap-3 rounded-lg border p-3 transition-colors",
        onSelect && "hover:border-primary/50 hover:bg-accent/50",
      )}
    >
      {/* Boton que cubre la tarjeta, para que el menu de acciones pueda ser
          otro boton sin anidarlos. */}
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
        {assets.length > 0 && (
          <div className="flex flex-wrap items-center gap-1">
            {assets.map((asset) => (
              <AssetBadge key={asset.id} kind={asset.kind} name={asset.name} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
