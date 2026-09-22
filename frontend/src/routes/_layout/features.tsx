import { createFileRoute } from "@tanstack/react-router"
import { CatalogPage } from "@/components/Catalog/CatalogPage"
import { validateFeatureSearch } from "@/components/Features/FeatureSearch"

export const Route = createFileRoute("/_layout/features")({
  component: () => <CatalogPage params={Route.useSearch()} />,
  validateSearch: validateFeatureSearch,
  head: () => ({ meta: [{ title: "Catálogo - INTEPLAST" }] }),
})
