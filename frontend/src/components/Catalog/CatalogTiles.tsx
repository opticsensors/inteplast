import type { ReactNode } from "react"
import type { FeaturePublic, PartCardPublic } from "@/client"
import { FeatureCoverStack } from "@/components/Features/FeatureCard"
import { partClassification, partName } from "@/components/Features/parts"
import {
  CorrectionsBadge,
  MeasurementBadge,
} from "@/components/Parts/MeasurementBadge"
import { PartThumbnail } from "@/components/Parts/PartCover"
import { cn } from "@/lib/utils"

/** Grid cell: large cover, then the identity. The colour edge tells the type apart. */
function Tile({
  label,
  cover,
  children,
  onSelect,
  actions,
  className,
}: {
  label: string
  cover: ReactNode
  children: ReactNode
  onSelect: () => void
  actions?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "relative flex min-w-0 flex-col overflow-hidden rounded-lg border border-t-4 transition-colors hover:border-primary/50 hover:bg-accent/50",
        className,
      )}
    >
      <button
        type="button"
        className="absolute inset-0 z-10 cursor-pointer rounded-lg"
        onClick={onSelect}
        title={label}
      >
        <span className="sr-only">Abrir {label}</span>
      </button>
      <div className="aspect-[4/3] w-full bg-muted p-2">{cover}</div>
      <div className="flex min-w-0 items-start gap-2 p-3">
        <div className="min-w-0 flex-1 space-y-0.5">{children}</div>
        {actions && <div className="relative z-20 shrink-0">{actions}</div>}
      </div>
    </div>
  )
}

export function PartTile({
  part,
  onSelect,
  actions,
}: {
  part: PartCardPublic
  onSelect: () => void
  actions?: ReactNode
}) {
  const name = partName(part)
  const classification = partClassification(part)
  return (
    <Tile
      label={name ? `${part.code} ${name}` : part.code}
      onSelect={onSelect}
      actions={actions}
      className="border-t-sky-500/60"
      cover={
        <PartThumbnail
          part={part}
          className="size-full border-0 bg-transparent"
          wrapperClassName="relative size-full"
        />
      }
    >
      <h3 className="truncate leading-tight">
        <span className="font-semibold">{part.code}</span>
        {name && (
          <>
            {" "}
            <span className="ml-1 text-muted-foreground">{name}</span>
          </>
        )}
      </h3>
      {classification && (
        <p className="truncate text-sm text-muted-foreground">
          {classification}
        </p>
      )}
      <div className="mt-1 flex min-w-0 flex-wrap gap-1">
        <MeasurementBadge
          status={part.measurement_status}
          className="max-w-full truncate"
        />
        <CorrectionsBadge
          documented={part.corrections_documented}
          className="max-w-full truncate"
        />
      </div>
    </Tile>
  )
}

export function FeatureTile({
  feature,
  onSelect,
  actions,
}: {
  feature: FeaturePublic
  onSelect: () => void
  actions?: ReactNode
}) {
  return (
    <Tile
      label={feature.name}
      onSelect={onSelect}
      actions={actions}
      className="border-t-primary/60"
      cover={
        <FeatureCoverStack
          feature={feature}
          className="size-full"
          flatClassName="border-0 bg-transparent"
        />
      }
    >
      <h3 className="line-clamp-2 break-words font-semibold leading-tight">
        {feature.name}
      </h3>
    </Tile>
  )
}
