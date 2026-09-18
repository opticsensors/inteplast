import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Folder, Loader2, Plus, Search, Trash2 } from "lucide-react"
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
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { featureParts, partLabel } from "./parts"
import { partFoldersQueryOptions, partsQueryOptions } from "./queries"
import { SaveStatus } from "./SaveStatus"
import { usePendingTask } from "./usePendingTask"

type PartChoice = {
  label: string
  folderPath?: string
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
  const folders = useQuery({ ...partFoldersQueryOptions(), enabled: open })
  const [search, setSearch] = useState("")
  const linkedIds = new Set(featureParts(feature).map((part) => part.id))
  const parts = catalog.data?.data ?? []
  const choices: PartChoice[] = (folders.data?.entries ?? []).map((folder) => {
    const code = /^(\d{1,64})(?:[\s_-]|$)/.exec(folder.name)?.[1]
    const part =
      parts.find((part) => part.folder_path === folder.path) ??
      parts.find((part) => !part.folder_path && part.code === code)
    return {
      label: part && part.name !== folder.name ? partLabel(part) : folder.name,
      folderPath: folder.path,
      part,
    }
  })
  // Keep older, manually registered pieces accessible, including unused trials.
  const matched = new Set(choices.map((choice) => choice.part?.id))
  choices.push(
    ...parts
      .filter((part) => !matched.has(part.id))
      .map((part) => ({
        label: partLabel(part),
        part,
      })),
  )
  const available = choices
    .filter(
      (choice) =>
        !linkedIds.has(choice.part?.id ?? "") &&
        `${choice.label} ${choice.folderPath ?? ""}`
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase()),
    )
    .sort((a, b) => a.label.localeCompare(b.label, "es", { numeric: true }))

  const add = useMutation({
    mutationFn: async (choice: PartChoice) => {
      const targetFeatureId = ensureFeatureId
        ? await ensureFeatureId()
        : feature.id
      // The endpoint also deduplicates retries after a failed feature link.
      const partId = choice.folderPath
        ? (
            await PartsService.createPartFromFolder({
              requestBody: { folder_path: choice.folderPath },
            })
          ).id
        : choice.part!.id
      await FeaturesService.linkFeaturePart({
        featureId: targetFeatureId,
        partId,
      })
      return partId
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
  const adding = usePendingTask((choice: PartChoice) => add.mutateAsync(choice))
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
            void queryClient.invalidateQueries({ queryKey: ["parts"] })
            void queryClient.invalidateQueries({ queryKey: ["part-folders"] })
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
            Anadir pieza
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
            {(folders.isLoading || catalog.isLoading) && (
              <output className="block px-2 py-3 text-sm text-muted-foreground">
                Cargando piezas…
              </output>
            )}
            {(folders.isError ||
              catalog.isError ||
              folders.data?.configured === false) && (
              <output className="block px-2 py-3 text-sm text-muted-foreground">
                {folders.data?.configured === false
                  ? "La carpeta principal de piezas no esta configurada."
                  : "No se ha podido cargar toda la lista de piezas."}
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  onClick={() => {
                    void folders.refetch()
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
                <div
                  key={choice.folderPath ?? part!.id}
                  className="flex items-center gap-1"
                >
                  <DropdownMenuItem
                    className="min-w-0 flex-1 flex-col items-start gap-0.5"
                    aria-label={choice.label}
                    disabled={
                      adding.pending ||
                      remove.isPending ||
                      catalog.isLoading ||
                      catalog.isError
                    }
                    onSelect={() => void adding.run(choice)}
                  >
                    <span className="flex max-w-full items-center gap-2">
                      {choice.folderPath && (
                        <Folder className="size-4 shrink-0" />
                      )}
                      <span className="truncate">{choice.label}</span>
                    </span>
                    {used && part && (
                      <span className="text-xs text-muted-foreground">
                        Usada en {part.feature_count} feature
                        {part.feature_count === 1 ? "" : "s"}
                      </span>
                    )}
                  </DropdownMenuItem>
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
            {available.length === 0 &&
              folders.isSuccess &&
              folders.data.configured &&
              catalog.isSuccess && (
                <p className="px-2 py-3 text-sm text-muted-foreground">
                  No hay piezas disponibles para esta busqueda.
                </p>
              )}
          </div>
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
