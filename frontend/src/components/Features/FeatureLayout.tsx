import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"
import { Badge } from "@/components/ui/badge"

export function FeatureBreadcrumb({
  name,
  kind = "feature",
}: {
  name: string
  kind?: "feature" | "part"
}) {
  return (
    <nav aria-label="Ruta de navegación" className="min-w-0 text-sm">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-muted-foreground">
        <li>
          <Link
            to="/features"
            className="hover:text-foreground hover:underline"
          >
            Catálogo
          </Link>
        </li>
        <li aria-hidden="true">/</li>
        <li>
          <Link
            to="/features"
            search={{ kind }}
            className="hover:text-foreground hover:underline"
          >
            {kind === "part" ? "Piezas" : "Features"}
          </Link>
        </li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" className="break-words text-foreground">
          {name}
        </li>
      </ol>
    </nav>
  )
}

export function FeatureSection({
  title,
  icon,
  count,
  children,
}: {
  title: string
  icon: ReactNode
  count?: number
  children: ReactNode
}) {
  return (
    <section
      aria-label={title}
      className="min-w-0 rounded-lg border bg-card p-4 sm:p-5"
    >
      <h2 className="mb-4 flex items-center gap-2.5 text-lg font-semibold">
        {icon}
        {title}
        {count !== undefined && (
          <Badge
            variant="secondary"
            className="rounded-full px-2.5 tabular-nums"
          >
            {count}
          </Badge>
        )}
      </h2>
      {children}
    </section>
  )
}

export const FEATURE_COLUMNS =
  "grid items-start gap-5 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]"
