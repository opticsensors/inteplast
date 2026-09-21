import { useId, useState } from "react"
import { SearchField } from "@/components/Common/SearchField"
import { normalizeCota } from "@/components/Features/drawingSearchHelpers"
import { cn } from "@/lib/utils"
import { findEntries } from "./measurementSelection"
import type { Entry } from "./types"

export function CotaSearch({
  entries,
  query,
  onQuery,
  onSelect,
}: {
  entries: Entry[]
  query: string
  onQuery: (query: string) => void
  onSelect: (code: string) => void
}) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const matches = findEntries(entries, query)
  const visible = matches.slice(0, 12)
  const current = Math.min(active, Math.max(0, visible.length - 1))
  const choose = (code: string) => {
    onSelect(code)
    setOpen(false)
  }
  return (
    <search
      className="relative z-20"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false)
      }}
    >
      <SearchField
        value={query}
        onValueChange={(value) => {
          onQuery(value)
          setOpen(true)
          setActive(0)
        }}
        onClear={() => {
          onQuery("")
          setActive(0)
          setOpen(false)
        }}
        placeholder="Buscar cota por número o descripción…"
        aria-label="Buscar cota"
        role="combobox"
        aria-expanded={open}
        aria-controls={id}
        aria-autocomplete="list"
        aria-activedescendant={
          open && visible.length ? `${id}-${current}` : undefined
        }
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false)
            return
          }
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault()
            setOpen(true)
            setActive(
              Math.max(
                0,
                Math.min(
                  visible.length - 1,
                  current + (event.key === "ArrowDown" ? 1 : -1),
                ),
              ),
            )
          }
          if (event.key === "Enter" && open) {
            event.preventDefault()
            if (visible[current]) choose(visible[current].id)
            else if (/^N?\s*\d+(?:\.\d+)?$/i.test(query.trim()))
              choose(normalizeCota(query))
          }
        }}
      />
      {open && (
        <div className="absolute top-full right-0 left-0 mt-1 overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md">
          <div
            id={id}
            role="listbox"
            aria-label="Cotas"
            className="max-h-72 overflow-y-auto p-1"
          >
            {visible.map((entry, index) => (
              <button
                id={`${id}-${index}`}
                type="button"
                role="option"
                aria-selected={index === current}
                key={entry.id}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(entry.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-sm px-3 py-2 text-left text-sm hover:bg-accent",
                  index === current && "bg-accent",
                )}
              >
                <span className="shrink-0 font-medium">
                  {entry.kind === "diagnostic" ? "Coordenadas" : entry.id}
                </span>
                <span className="truncate text-muted-foreground">
                  {entry.title}
                </span>
              </button>
            ))}
            {!visible.length && (
              <p className="p-3 text-sm text-muted-foreground">
                Sin cotas con mediciones para esta búsqueda.
              </p>
            )}
          </div>
          {matches.length > visible.length && (
            <p className="border-t px-4 py-2 text-xs text-muted-foreground">
              {matches.length} resultados. Escribe para concretar la búsqueda.
            </p>
          )}
        </div>
      )}
    </search>
  )
}
