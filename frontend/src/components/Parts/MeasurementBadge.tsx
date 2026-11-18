import type { PartCardPublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const LABELS = {
  detected: {
    text: "Medidas detectadas",
    className: "border-emerald-500/40 text-emerald-700 dark:text-emerald-300",
  },
  pending: {
    text: "Informe pendiente de interpretar",
    className: "border-amber-500/40 text-amber-700 dark:text-amber-300",
  },
  none: {
    text: "Sin medidas detectadas",
    className: "text-muted-foreground",
  },
} as const

/** What the app read from the piece's measurement reports; nothing before reading. */
export function MeasurementBadge({
  status,
  className,
}: {
  status: PartCardPublic["measurement_status"]
  className?: string
}) {
  if (!status) return null
  const label = LABELS[status]
  return (
    <Badge
      variant="outline"
      className={cn("shrink-0 font-normal", label.className, className)}
    >
      {label.text}
    </Badge>
  )
}

/** «Documentación de retoques»: the read found correction documents. Positive only. */
export function CorrectionsBadge({
  documented,
  className,
}: {
  documented: PartCardPublic["corrections_documented"]
  className?: string
}) {
  if (!documented) return null
  return (
    <Badge
      variant="outline"
      className={cn(
        "shrink-0 border-violet-500/40 font-normal text-violet-700 dark:text-violet-300",
        className,
      )}
    >
      Documentación de retoques
    </Badge>
  )
}
