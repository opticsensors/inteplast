import { createFileRoute } from "@tanstack/react-router"
import { NewPartPage } from "@/components/Parts/PartDetailPage"

export const Route = createFileRoute("/_layout/parts_/nueva")({
  component: NewPartPage,
  head: () => ({ meta: [{ title: "Nueva pieza - INTEPLAST" }] }),
})
