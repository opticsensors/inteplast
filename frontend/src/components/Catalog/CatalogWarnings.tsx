import { TriangleAlert } from "lucide-react"

import type { FeaturePublic, PartCardPublic } from "@/client"

export function PartWarnings({ part }: { part: PartCardPublic }) {
  const warnings: string[] = []
  if (
    part.measurement_status === "none" ||
    part.measurement_status === "pending"
  )
    warnings.push("Sin mediciones detectadas")
  if (part.corrections_missing) warnings.push("Sin correcciones detectadas")
  if (part.feature_count === 0) warnings.push("Sin features asociados")
  return <WarningList label="Avisos de la pieza" warnings={warnings} />
}

export function FeatureWarnings({ feature }: { feature: FeaturePublic }) {
  if (feature.part_count !== 0) return null
  return (
    <WarningList
      label="Avisos del feature"
      warnings={["Sin piezas asociadas"]}
    />
  )
}

function WarningList({
  label,
  warnings,
}: {
  label: string
  warnings: string[]
}) {
  if (!warnings.length) return null

  return (
    <ul
      aria-label={label}
      className="flex flex-wrap gap-x-3 gap-y-1 pt-1 text-xs text-amber-800 dark:text-amber-300"
    >
      {warnings.map((warning) => (
        <li key={warning} className="flex items-start gap-1.5">
          <TriangleAlert
            aria-hidden="true"
            className="mt-px size-3.5 shrink-0"
          />
          {warning}
        </li>
      ))}
    </ul>
  )
}
