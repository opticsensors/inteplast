import { LayoutGrid, List, Share2 } from "lucide-react"
import { Button } from "@/components/ui/button"

export type CatalogView = "list" | "grid" | "graph"

const STORAGE_KEY = "inteplast.catalog-view"
const VIEWS: CatalogView[] = ["list", "grid", "graph"]

/**
 * The view chosen last time, kept in this browser only. If storage is blocked or holds
 * anything else, the catalogue opens as a list without errors.
 */
export function readCatalogView(): CatalogView {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    return VIEWS.includes(saved as CatalogView)
      ? (saved as CatalogView)
      : "list"
  } catch {
    return "list"
  }
}

export function saveCatalogView(view: CatalogView) {
  try {
    window.localStorage.setItem(STORAGE_KEY, view)
  } catch {
    // Private windows or blocked storage: the choice lasts until the page closes.
  }
}

const OPTIONS: { value: CatalogView; label: string; icon: typeof List }[] = [
  { value: "list", label: "Lista", icon: List },
  { value: "grid", label: "Cuadrícula", icon: LayoutGrid },
  { value: "graph", label: "Grafo", icon: Share2 },
]

/** Lista · Cuadrícula · Grafo, beside the search. */
export function CatalogViewSwitch({
  value,
  onChange,
}: {
  value: CatalogView
  onChange: (view: CatalogView) => void
}) {
  return (
    <fieldset
      aria-label="Vista"
      className="flex h-11 shrink-0 rounded-md border p-0.5"
    >
      {OPTIONS.map(({ value: option, label, icon: Icon }) => (
        <Button
          key={option}
          type="button"
          variant="ghost"
          aria-pressed={value === option}
          aria-label={label}
          title={label}
          className="h-full px-2.5 text-muted-foreground aria-pressed:bg-accent aria-pressed:text-foreground"
          onClick={() => onChange(option)}
        >
          <Icon className="size-4" />
          <span className="hidden lg:inline">{label}</span>
        </Button>
      ))}
    </fieldset>
  )
}
