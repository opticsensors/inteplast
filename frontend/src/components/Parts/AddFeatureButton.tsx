import { useQuery } from "@tanstack/react-query"
import { Plus, Search } from "lucide-react"
import { useRef, useState } from "react"
import { featureFiltersQueryOptions } from "@/components/Features/queries"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"

export function AddFeatureButton({
  linkedIds,
  disabled,
  onSelect,
}: {
  linkedIds: string[]
  disabled: boolean
  onSelect: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const firstFeature = useRef<HTMLDivElement>(null)
  const catalog = useQuery(featureFiltersQueryOptions())
  const available = (catalog.data?.features ?? [])
    .filter(
      (feature) =>
        !linkedIds.includes(feature.id) &&
        feature.name
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase()),
    )
    .sort((a, b) => a.name.localeCompare(b.name, "es", { numeric: true }))

  return (
    <DropdownMenu
      open={open}
      onOpenChange={(value) => {
        setOpen(value)
        if (value) {
          setSearch("")
          void catalog.refetch()
        }
      }}
    >
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="sm" disabled={disabled}>
          <Plus className="mr-1 size-3.5" />
          Añadir feature
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="w-80 max-w-[calc(100vw-2rem)]"
      >
        <div className="flex items-center gap-2 p-2">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <Input
            aria-label="Buscar feature"
            placeholder="Buscar por nombre"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Escape" && event.key !== "Tab")
                event.stopPropagation()
              if (event.key === "ArrowDown" && !catalog.isError && !disabled) {
                event.preventDefault()
                firstFeature.current?.focus()
              }
            }}
            className="h-8"
          />
        </div>
        <div className="max-h-60 overflow-y-auto">
          {catalog.isLoading && (
            <output className="block px-2 py-3 text-sm text-muted-foreground">
              Cargando features…
            </output>
          )}
          {catalog.isError && (
            <output className="block px-2 py-3 text-sm text-muted-foreground">
              No se ha podido cargar la lista de features.
              <Button
                type="button"
                variant="link"
                size="sm"
                onClick={() => void catalog.refetch()}
              >
                Reintentar
              </Button>
            </output>
          )}
          {available.map((feature, index) => (
            <DropdownMenuItem
              key={feature.id}
              ref={index === 0 ? firstFeature : undefined}
              aria-label={feature.name}
              disabled={disabled || catalog.isLoading || catalog.isError}
              onSelect={() => onSelect(feature.id)}
            >
              <span className="truncate">{feature.name}</span>
            </DropdownMenuItem>
          ))}
          {!available.length && catalog.isSuccess && (
            <p className="px-2 py-3 text-sm text-muted-foreground">
              No hay features disponibles.
            </p>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
