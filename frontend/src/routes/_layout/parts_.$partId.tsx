import { createFileRoute } from "@tanstack/react-router"
import { validatePartSearch } from "@/components/Parts/measurementSelection"
import { PartDetailPage } from "@/components/Parts/PartDetailPage"

export const Route = createFileRoute("/_layout/parts_/$partId")({
  component: () => (
    <PartDetailPage
      partId={Route.useParams().partId}
      search={Route.useSearch()}
    />
  ),
  validateSearch: validatePartSearch,
  head: () => ({ meta: [{ title: "Pieza - INTEPLAST" }] }),
})
