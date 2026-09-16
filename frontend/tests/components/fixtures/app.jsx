import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Link,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router"
import { createRoot } from "react-dom/client"
import { Toaster } from "sonner"
import { FileLink } from "../../../src/components/Common/FileLink"
import { FeatureCover } from "../../../src/components/Features/FeatureCover"
import { FeatureForm } from "../../../src/components/Features/FeatureForm"
import { PartAssetList } from "../../../src/components/Features/PartAssetList"
import useAuth from "../../../src/hooks/useAuth"
import { Route as LoginRoute } from "../../../src/routes/login"

localStorage.setItem(
  "access_token",
  `x.${btoa(JSON.stringify({ exp: Date.now() / 1000 + 3600 }))}.x`,
)

function LogoutButton() {
  const { logout } = useAuth()
  return (
    <button
      type="button"
      onClick={() => {
        void logout()
      }}
    >
      Cerrar sesion
    </button>
  )
}

window.review = {
  feature: {
    id: "feature-one",
    name: "Original header",
    description: "Original description",
    category: null,
    tags: [],
    image: null,
    notes: [
      {
        id: "note-one",
        title: "Original warning",
        body: "Original body",
        kind: "warning",
        position: 0,
      },
    ],
    parts: [{ id: "part-one", code: "3212", name: "Pump Housing" }],
    assets: [
      {
        id: "asset-one",
        kind: "mold",
        name: "Original asset",
        position: 0,
        part: { id: "part-one", code: "3212", name: "Pump Housing" },
        file: null,
      },
    ],
  },
  requests: [],
  accessRequests: [],
  uploadRequests: [],
  failNotes: false,
  delay: 0,
}
const client = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})
window.review.refetch = () =>
  client.invalidateQueries({ queryKey: ["features"] })
const root = createRootRoute({ component: () => <Outlet /> })
const editor = createRoute({
  getParentRoute: () => root,
  path: "/",
  component: () => (
    <>
      <Link to="/away">Otra pagina</Link>
      <LogoutButton />
      <FeatureForm
        featureId="feature-one"
        onSaved={() => router.navigate({ to: "/away" })}
        onCancel={() => router.navigate({ to: "/away" })}
        onCreated={() => {}}
      />
    </>
  ),
})
const away = createRoute({
  getParentRoute: () => root,
  path: "/away",
  component: () => <h1>Otra pagina abierta</h1>,
})
const files = createRoute({
  getParentRoute: () => root,
  path: "/files",
  component: () => (
    <FileLink fileId="file-one" downloadFile>
      Descargar prueba
    </FileLink>
  ),
})
const previews = createRoute({
  getParentRoute: () => root,
  path: "/previews",
  component: () => <PartAssetList feature={window.review.feature} />,
})
const cover = createRoute({
  getParentRoute: () => root,
  path: "/cover",
  component: () => <FeatureCover feature={window.review.feature} />,
})
const router = createRouter({
  routeTree: root.addChildren([
    editor,
    away,
    files,
    previews,
    cover,
    LoginRoute.update({
      id: "/login",
      path: "/login",
      getParentRoute: () => root,
    }),
  ]),
  history: createMemoryHistory({ initialEntries: ["/"] }),
})
window.review.navigate = (to) => router.navigate({ to })
createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={client}>
    <RouterProvider router={router} />
    <Toaster />
  </QueryClientProvider>,
)
