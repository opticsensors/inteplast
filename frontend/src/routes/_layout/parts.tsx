import { createFileRoute, redirect } from "@tanstack/react-router"
import { validatePartSearch } from "@/components/Parts/measurementSelection"

export const Route = createFileRoute("/_layout/parts")({
  validateSearch: validatePartSearch,
  beforeLoad: ({ search }) => {
    throw redirect({
      to: "/features",
      search: {
        q: search.q ?? search.cota,
        feature: search.feature,
        category: search.category,
        tag: search.tag,
        kind: "part",
      },
      replace: true,
    })
  },
})
