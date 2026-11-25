import { useQueries } from "@tanstack/react-query"
import { TriangleAlert } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { FeaturePublic, PartCardPublic } from "@/client"
import { coverQuery, useCatalogCover } from "@/hooks/useCatalogCover"

export function PartWarnings({ part }: { part: PartCardPublic }) {
  const warnings: string[] = []
  if (
    part.measurement_status === "none" ||
    part.measurement_status === "pending"
  )
    warnings.push("Sin mediciones detectadas")
  if (part.corrections_missing) warnings.push("Sin correcciones detectadas")
  if (part.feature_count === 0) warnings.push("Sin features asociados")
  return (
    <>
      <WarningList label="Avisos de la pieza" warnings={warnings} />
      {part.has_face_marks && <PartFaceWarning partId={part.id} />}
    </>
  )
}

export function FeatureWarnings({ feature }: { feature: FeaturePublic }) {
  if (feature.part_count !== 0) return <FeatureFaceWarning feature={feature} />
  return (
    <WarningList
      label="Avisos del feature"
      warnings={["Sin piezas asociadas"]}
    />
  )
}

export function FaceReviewList({
  review,
}: {
  review?: Record<string, string>
}) {
  const names = Object.values(review ?? {}).sort((a, b) => a.localeCompare(b))
  return (
    <WarningList
      label="Selección de caras"
      warnings={names.length ? [`Caras por revisar: ${names.join(", ")}`] : []}
    />
  )
}

function PartFaceWarning({ partId }: { partId: string }) {
  const { ref, cover } = useCatalogCover(partId)
  return (
    <div ref={ref}>
      <FaceReviewList review={cover?.face_colors?.review} />
    </div>
  )
}

export function FeatureFaceWarning({ feature }: { feature: FeaturePublic }) {
  return feature.marked_part_ids?.length ? (
    <MarkedFeatureWarning feature={feature} />
  ) : null
}

function MarkedFeatureWarning({ feature }: { feature: FeaturePublic }) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    if (!ref.current) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: "200px" },
    )
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])
  const results = useQueries({
    queries: (feature.marked_part_ids ?? []).map((id) => ({
      ...coverQuery(id),
      enabled: visible,
    })),
  })
  const count = results.filter(
    (q) => q.isSuccess && q.data.face_colors?.review[feature.id],
  ).length
  return (
    <div ref={ref}>
      <WarningList
        label="Selección de caras"
        warnings={
          count
            ? [
                `Caras por revisar en ${count} ${count === 1 ? "pieza" : "piezas"}`,
              ]
            : []
        }
      />
    </div>
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
