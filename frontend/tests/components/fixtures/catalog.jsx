import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  Outlet,
  RouterProvider,
  stringifySearchWith,
} from "@tanstack/react-router"
import { createRoot } from "react-dom/client"
import { Toaster } from "sonner"
import { FeaturesService, UsersService } from "@/client"
import { Route as Layout } from "../../../src/routes/_layout"
import { Route as Catalog } from "../../../src/routes/_layout/features"
import { Route as Detail } from "../../../src/routes/_layout/features_.$featureId"
import { Route as NewFeature } from "../../../src/routes/_layout/features_.nuevo"
import { Route as Home } from "../../../src/routes/_layout/index"

localStorage.setItem(
  "access_token",
  `x.${btoa(JSON.stringify({ exp: Date.now() / 1000 + 3600 }))}.x`,
)
window.review = {
  feature: {
    id: "feature-one",
    name: "Bolt Eye",
    description: "Referencia de diseño para el 3212 Pump Housing",
    owner_id: "test-user",
    category: "hole",
    tags: ["inyeccion"],
    image: null,
    notes: [],
    parts: [{ id: "part-one", code: "3212", name: "Pump Housing" }],
    assets: [],
  },
  user: { id: "test-user", email: "review@example.com", is_superuser: false },
  requests: [],
  deleted: false,
}
const clone = (value) => structuredClone(value)
FeaturesService.readFeatures = async () => ({
  data: window.review.deleted ? [] : [clone(window.review.feature)],
  count: window.review.deleted ? 0 : 1,
})
FeaturesService.readFeatureFilters = async () => ({
  parts: clone(window.review.feature.parts),
  categories: ["hole"],
  tags: ["inyeccion"],
})
FeaturesService.createFeature = async ({ requestBody }) => {
  Object.assign(window.review.feature, requestBody)
  return clone(window.review.feature)
}
FeaturesService.deleteFeature = async () => {
  window.review.deleted = true
  return { message: "Deleted" }
}
UsersService.readUserMe = async () => clone(window.review.user)

const root = createRootRoute({ component: () => <Outlet /> })
const layout = Layout.update({ id: "/_layout", getParentRoute: () => root })
const routes = [
  [Home, "/", "/"],
  [Catalog, "/features", "/features"],
  [Detail, "/features_/$featureId", "/features/$featureId"],
  [NewFeature, "/features_/nuevo", "/features/nuevo"],
].map(([route, id, path]) =>
  route.update({ id, path, getParentRoute: () => layout }),
)
const client = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})
const router = createRouter({
  routeTree: root.addChildren([layout.addChildren(routes)]),
  history: createMemoryHistory({
    initialEntries: [window.catalogInitialPath ?? "/"],
  }),
  stringifySearch: stringifySearchWith(JSON.stringify),
})
window.review.location = () => router.state.location
window.review.back = () => router.history.back()
window.review.refreshUser = () =>
  client.invalidateQueries({ queryKey: ["currentUser"] })

createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={client}>
    <RouterProvider router={router} />
    <Toaster />
  </QueryClientProvider>,
)
