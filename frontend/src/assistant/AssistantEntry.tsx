import { useQuery } from "@tanstack/react-query"
import { lazy, Suspense } from "react"
import { ErrorBoundary } from "react-error-boundary"
import { getStatus } from "./api"

const AssistantWidget = lazy(() => import("./AssistantWidget"))

/** The only application mount. History survives route changes, not logout/reload. */
export function AssistantEntry() {
  const { data } = useQuery({
    queryKey: ["assistant-status"],
    queryFn: ({ signal }) => getStatus(signal),
    staleTime: 60_000,
    retry: false,
  })
  if (!data?.enabled) return null
  return (
    <ErrorBoundary
      fallback={
        <p className="fixed bottom-4 right-4 z-40 rounded-lg border bg-background p-3 text-sm">
          El asistente no está disponible. Recarga la página para reintentarlo.
        </p>
      }
    >
      <Suspense fallback={null}>
        <AssistantWidget />
      </Suspense>
    </ErrorBoundary>
  )
}
