import { createFileRoute, redirect } from "@tanstack/react-router"

import { validateFeatureSearch } from "@/components/Features/FeatureSearch"

export const Route = createFileRoute("/_layout/")({
  validateSearch: validateFeatureSearch,
  beforeLoad: ({ search }) => {
    // Conserva los enlaces y favoritos del antiguo buscador de inicio.
    throw redirect({ to: "/features", search, replace: true })
  },
})
