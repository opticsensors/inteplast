import type { ReactNode } from "react"
import type { PartCardPublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { PartThumbnail } from "./PartCover"

export function PartCard({
  part,
  onSelect,
  actions,
}: {
  part: PartCardPublic
  onSelect: () => void
  actions?: ReactNode
}) {
  return (
    <div className="relative flex gap-3 rounded-lg border border-l-4 border-l-sky-500/60 p-3 transition-colors hover:border-primary/50 hover:bg-accent/50">
      <button
        type="button"
        className="absolute inset-0 z-10 cursor-pointer rounded-lg"
        onClick={onSelect}
      >
        <span className="sr-only">Abrir {part.name ?? part.code}</span>
      </button>
      <PartThumbnail part={part} className="size-24 self-center sm:size-36" />
      <div className="h-36 min-w-0 flex-1 space-y-1.5">
        <div className="flex items-start gap-2">
          <h3 className="line-clamp-2 min-w-0 flex-1 break-words font-semibold leading-tight">
            {part.name ?? part.code}
          </h3>
          {actions && <div className="relative z-20 shrink-0">{actions}</div>}
        </div>
        <Badge
          variant="outline"
          className="border-sky-500/40 text-sky-700 dark:text-sky-300"
        >
          Pieza
        </Badge>
        <p className="font-mono text-sm text-muted-foreground">{part.code}</p>
        <p className="text-sm text-muted-foreground">
          {part.feature_count} features · {part.characteristic_count} cotas
        </p>
      </div>
    </div>
  )
}
