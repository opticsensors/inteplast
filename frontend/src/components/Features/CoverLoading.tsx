import { LoaderCircle } from "lucide-react"

/** Kept small and transparent so the saved cover remains visible. */
export function CoverLoading() {
  return (
    <output className="pointer-events-none absolute inset-x-2 bottom-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
      <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" />
      Cargando modelo CAD…
    </output>
  )
}
