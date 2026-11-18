import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import {
  createRouter,
  RouterProvider,
  stringifySearchWith,
} from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ApiError, OpenAPI } from "./client"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import { routeTree } from "./routeTree.gen"

/**
 * A tab opened before a rebuild still asks for chunks of the previous build (3D viewer,
 * cover editor…), which no longer exist. Reload once to get the new build instead of
 * showing the error page; never twice in a row, so a real failure still shows.
 */
const RELOADED_AT = "inteplast.chunk-reload"
window.addEventListener("vite:preloadError", (event) => {
  let last = 0
  try {
    last = Number(sessionStorage.getItem(RELOADED_AT) ?? 0)
  } catch {
    // Without storage, reloading once per error is still better than a dead page.
  }
  if (Date.now() - last < 30_000) return
  event.preventDefault()
  try {
    sessionStorage.setItem(RELOADED_AT, String(Date.now()))
  } catch {
    // Same as above.
  }
  window.location.reload()
})

OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}

const isAuthError = (error: Error) =>
  error instanceof ApiError && [401, 403].includes(error.status)

const logOutAndRedirect = () => {
  localStorage.removeItem("access_token")
  window.location.href = "/login"
}

const handleApiError = (error: Error) => {
  if (isAuthError(error)) {
    logOutAndRedirect()
  }
}

/**
 * Si la consulta del usuario actual falla, el token no sirve, diga lo que diga
 * el backend. Sin esta red de seguridad basta un codigo de error inesperado
 * para dejar la aplicacion en un limbo: sesion iniciada, usuario desconocido,
 * menu incompleto y ningun sitio donde pulsar para salir.
 */
const handleQueryError = (
  error: Error,
  query: { queryKey: readonly unknown[] },
) => {
  if (query.queryKey[0] === "currentUser") {
    logOutAndRedirect()
    return
  }
  handleApiError(error)
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Reintentar un 401/403 no lo va a arreglar, y con los reintentos por
      // defecto la pantalla se queda vacia 7 segundos antes de mandarte al
      // login. Con credenciales malas, a la primera.
      retry: (failureCount, error) => !isAuthError(error) && failureCount < 3,
    },
  },
  queryCache: new QueryCache({
    onError: handleQueryError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

/**
 * Sin esto, el router entrecomilla en la URL cualquier texto que parezca JSON
 * para conservar el tipo al volver: buscar `3212` daba `/?q=%223212%22`. Y un
 * codigo de pieza es justo lo que mas se busca aqui. Pasando `JSON.stringify`
 * sin parser, las cadenas viajan tal cual (`/?q=3212`) y al leerlas vuelven
 * como numero — de eso se encarga `validateFeatureSearch`.
 */
const router = createRouter({
  routeTree,
  scrollRestoration: true,
  getScrollRestorationKey: (location) => location.pathname,
  stringifySearch: stringifySearchWith(JSON.stringify),
})
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
