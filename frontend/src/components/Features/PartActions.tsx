import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, Plus, Search, Trash2 } from "lucide-react"
import { useState } from "react"

import {
  type FeaturePublic,
  FeaturesService,
  type PartCatalogPublic,
  PartsService,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { featureParts, partLabel } from "./parts"
import { partsQueryOptions } from "./queries"
import { SaveStatus } from "./SaveStatus"
import { usePendingTask } from "./usePendingTask"

type PartChoice = {
  label: string
  part?: PartCatalogPublic
}

export function PartActions({
  feature,
  onAdded,
  ensureFeatureId,
}: {
  feature: FeaturePublic
  onAdded: (partId: string) => void
  ensureFeatureId?: () => Promise<string>
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const { user } = useAuth()
  const catalog = useQuery(partsQueryOptions())
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const linkedIds = new Set(featureParts(feature).map((part) => part.id))
  const parts = catalog.data?.data ?? []
  const choices: PartChoice[] = parts.map((part) => ({
    label: partLabel(part),
    part,
  }))
  const available = choices
    .filter(
      (choice) =>
        !linkedIds.has(choice.part?.id ?? "") &&
        choice.label
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase()),
    )
    .sort((a, b) => a.label.localeCompare(b.label, "es", { numeric: true }))

  // Several pieces can be ticked and added at once (plan de portadas, Interfaz).
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  const toggle = (partId: string) =>
    setSelected((current) => {
      const next = new Set(current)
      if (!next.delete(partId)) next.add(partId)
      return next
    })
  const add = useMutation({
    mutationFn: async (partIds: string[]) => {
      const targetFeatureId = ensureFeatureId
        ? await ensureFeatureId()
        : feature.id
      // One by one: linking is idempotent, so a retry after a failure is safe.
      for (const partId of partIds)
        await FeaturesService.linkFeaturePart({
          featureId: targetFeatureId,
          partId,
        })
      return partIds[partIds.length - 1]
    },
    onSuccess: onAdded,
    onError: handleError.bind(showErrorToast),
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["parts"] }),
        queryClient.invalidateQueries({ queryKey: ["features"] }),
      ])
    },
  })
  const adding = usePendingTask((partIds: string[]) => add.mutateAsync(partIds))
  // Everything ticked, also what the current search hides; never a piece already in.
  const chosen = choices
    .map((choice) => choice.part!.id)
    .filter((partId) => selected.has(partId) && !linkedIds.has(partId))
  const remove = useMutation({
    mutationFn: (partId: string) => PartsService.deletePart({ partId }),
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ["parts"] }),
        queryClient.invalidateQueries({ queryKey: ["features"] }),
      ]),
  })

  return (
    <div>
      <DropdownMenu
        open={open}
        onOpenChange={(open) => {
          setOpen(open)
          if (open) {
            setSearch("")
            setSelected(new Set())
            void queryClient.invalidateQueries({ queryKey: ["parts"] })
          }
        }}
      >
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={adding.pending || remove.isPending}
          >
            <Plus className="mr-1 size-3.5" />
            Añadir pieza
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          className="w-80 max-w-[calc(100vw-2rem)]"
        >
          <div className="flex items-center gap-2 p-2">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <Input
              aria-label="Buscar pieza"
              placeholder="Buscar por codigo o nombre"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key !== "Escape" && event.key !== "Tab")
                  event.stopPropagation()
              }}
              className="h-8"
            />
          </div>
          <div className="max-h-60 overflow-y-auto">
            {catalog.isLoading && (
              <output className="block px-2 py-3 text-sm text-muted-foreground">
                Cargando piezas…
              </output>
            )}
            {catalog.isError && (
              <output className="block px-2 py-3 text-sm text-muted-foreground">
                No se ha podido cargar la lista de piezas.
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  onClick={() => {
                    void catalog.refetch()
                  }}
                >
                  Reintentar
                </Button>
              </output>
            )}
            {available.map((choice) => {
              const { part } = choice
              const used = (part?.feature_count ?? 0) > 0
              const reason = used
                ? "Desvincula la pieza de sus features antes de eliminarla"
                : !user?.is_superuser
                  ? "Solo un administrador puede eliminar piezas del catálogo"
                  : "Eliminar pieza del catálogo"
              return (
                <div key={part!.id} className="flex items-center gap-1">
                  <DropdownMenuCheckboxItem
                    className="min-w-0 flex-1 flex-col items-start gap-0.5"
                    aria-label={choice.label}
                    checked={selected.has(part!.id)}
                    disabled={
                      adding.pending ||
                      remove.isPending ||
                      catalog.isLoading ||
                      catalog.isError
                    }
                    // Ticking keeps the menu open to choose more pieces.
                    onSelect={(event) => event.preventDefault()}
                    onCheckedChange={() => toggle(part!.id)}
                  >
                    <span className="flex max-w-full items-center gap-2">
                      <span className="truncate">{choice.label}</span>
                    </span>
                    {used && part && (
                      <span className="text-xs text-muted-foreground">
                        Usada en {part.feature_count} feature
                        {part.feature_count === 1 ? "" : "s"}
                      </span>
                    )}
                  </DropdownMenuCheckboxItem>
                  {part && (
                    <span title={reason}>
                      <DropdownMenuItem
                        className="size-8 shrink-0 justify-center p-0"
                        variant="destructive"
                        aria-label={`Eliminar ${choice.label}`}
                        disabled={
                          used || !user?.is_superuser || remove.isPending
                        }
                        onSelect={(event) => {
                          event.preventDefault()
                          remove.mutate(part.id)
                        }}
                      >
                        {remove.isPending && remove.variables === part.id ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="size-3.5" />
                        )}
                      </DropdownMenuItem>
                    </span>
                  )}
                </div>
              )
            })}
            {available.length === 0 && catalog.isSuccess && (
              <p className="px-2 py-3 text-sm text-muted-foreground">
                No hay piezas disponibles. Crea una con Nueva pieza en Catálogo.
              </p>
            )}
          </div>
          {(available.length > 0 || chosen.length > 0) && (
            <div className="border-t p-2">
              <Button
                type="button"
                size="sm"
                className="w-full"
                disabled={!chosen.length || adding.pending || remove.isPending}
                onClick={() => {
                  setOpen(false)
                  void adding.run(chosen)
                }}
              >
                {chosen.length === 1
                  ? "Añadir 1 pieza"
                  : `Añadir ${chosen.length} piezas`}
              </Button>
            </div>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      <SaveStatus
        error={adding.error}
        saving={adding.pending}
        retry={adding.retry}
      />
    </div>
  )
}
