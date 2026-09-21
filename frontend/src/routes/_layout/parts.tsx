import { createFileRoute } from "@tanstack/react-router"
import { MetrologyPage } from "@/components/Parts/MetrologyPage"
import { validatePartSearch } from "@/components/Parts/measurementSelection"

export const Route = createFileRoute("/_layout/parts")({
  component: () => <MetrologyPage search={Route.useSearch()} />,
  validateSearch: validatePartSearch,
  head: () => ({ meta: [{ title: "Metrología - INTEPLAST" }] }),
})
