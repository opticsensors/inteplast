import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { MoreHorizontal, Trash2 } from "lucide-react"
import { useState } from "react"

import { type PartDeletionScope, PartsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { Skeleton } from "@/components/ui/skeleton"
import useCustomToast from "@/hooks/useCustomToast"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { PIECE_QUERY_KEYS } from "./PartReadStatus"

function plural(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`
}

/** Lo que se elimina, en frases; omite lo que no hay. */
export function deletionLines(scope: PartDeletionScope): string[] {
  const lines: string[] = []
  if (scope.characteristics)
    lines.push(plural(scope.characteristics, "cota", "cotas"))
  if (scope.measurement_imports)
    lines.push(
      plural(
        scope.measurement_imports,
        "medición importada",
        "mediciones importadas",
      ),
    )
  if (scope.files_removed)
    lines.push(
      `${plural(scope.files_removed, "documento vinculado", "documentos vinculados")}${
        scope.uploads_removed
          ? ` (${plural(scope.uploads_removed, "subido a la app", "subidos a la app")})`
          : ""
      }`,
    )
  if (scope.reviewed_locations)
    lines.push(
      plural(
        scope.reviewed_locations,
        "ubicación revisada en el plano",
        "ubicaciones revisadas en el plano",
      ),
    )
  if (scope.feature_characteristic_links)
    lines.push(
      plural(
        scope.feature_characteristic_links,
        "cota asignada a un feature",
        "cotas asignadas a features",
      ),
    )
  if (scope.feature_assets)
    lines.push(
      plural(
        scope.feature_assets,
        "adjunto de feature",
        "adjuntos de features",
      ),
    )
  if (scope.covers_reset)
    lines.push(
      plural(
        scope.covers_reset,
        "portada 3D de feature hecha con esta pieza",
        "portadas 3D de features hechas con esta pieza",
      ),
    )
  return lines
}

export function DeletePart({
  partId,
  onDeleted,
}: {
  partId: string
  onDeleted: () => void
}) {
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState("")
  const client = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const scope = useQuery({
    queryKey: ["parts", "deletion", partId],
    queryFn: () => PartsService.readPartDeletion({ partId }),
    enabled: open,
    gcTime: 0,
    staleTime: 0,
  })
  const remove = useMutation({
    mutationFn: (key: string) =>
      PartsService.deletePart({ partId, confirm: key }),
    onSuccess: async () => {
      showSuccessToast("Pieza eliminada")
      setOpen(false)
      onDeleted()
      await Promise.all(
        [...PIECE_QUERY_KEYS, "features"].map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      )
    },
    onError: () => {
      // The scope may have changed: show the current one again.
      void scope.refetch()
    },
  })
  const data = scope.data
  const lines = data ? deletionLines(data) : []
  const features = data?.features ?? []
  const kept = data?.files_kept ?? 0
  const confirmed = Boolean(data) && typed.trim() === data?.code
  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (remove.isPending) return
        setOpen(value)
        setTyped("")
        remove.reset()
      }}
    >
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            aria-label="Más acciones de la pieza"
          >
            <MoreHorizontal />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            variant="destructive"
            onSelect={() => setOpen(true)}
          >
            <Trash2 />
            Eliminar
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Eliminar pieza</DialogTitle>
          <DialogDescription>
            Se eliminará la pieza con sus datos en la aplicación. Esta acción no
            se puede deshacer.
          </DialogDescription>
        </DialogHeader>
        {scope.isPending && (
          <div className="space-y-2">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}
        {scope.isError && (
          <p role="alert" className="text-sm text-destructive">
            {fileErrorMessage(scope.error)}
          </p>
        )}
        {data && (
          <div className="space-y-4 text-sm">
            <p>
              <span className="font-medium">{data.code}</span>
              {data.name && data.name !== data.code && (
                <span className="text-muted-foreground"> · {data.name}</span>
              )}
            </p>
            <section aria-label="Se elimina">
              <h3 className="mb-1 font-medium">Se elimina</h3>
              {lines.length ? (
                <ul className="list-disc space-y-0.5 pl-5">
                  {lines.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">
                  Solo la ficha: no tiene datos ni documentos.
                </p>
              )}
            </section>
            <section aria-label="Se conserva">
              <h3 className="mb-1 font-medium">Se conserva</h3>
              <ul className="list-disc space-y-0.5 pl-5">
                <li>
                  Los archivos y carpetas originales de INTEPLAST, en local y en
                  SharePoint.
                </li>
                {features.length > 0 && (
                  <li>
                    {features.length === 1
                      ? "El feature "
                      : `Los ${features.length} features `}
                    {features.map((f) => `«${f.name}»`).join(", ")}, con sus
                    advertencias, lecciones y las demás piezas. Solo pierden
                    esta pieza.
                  </li>
                )}
                {kept > 0 && (
                  <li>
                    {plural(
                      kept,
                      "documento que también usa otra pieza o feature",
                      "documentos que también usan otras piezas o features",
                    )}
                    .
                  </li>
                )}
              </ul>
            </section>
            <div className="grid gap-2">
              <Label htmlFor="delete-part-code">
                Escribe el código <span className="font-mono">{data.code}</span>{" "}
                para confirmar
              </Label>
              <Input
                id="delete-part-code"
                autoComplete="off"
                value={typed}
                disabled={remove.isPending}
                onChange={(event) => setTyped(event.target.value)}
              />
            </div>
          </div>
        )}
        {remove.error && (
          <p role="alert" className="text-sm text-destructive">
            {fileErrorMessage(remove.error)}
          </p>
        )}
        <DialogFooter className="mt-2">
          <DialogClose asChild>
            <Button variant="outline" disabled={remove.isPending}>
              Cancelar
            </Button>
          </DialogClose>
          <LoadingButton
            variant="destructive"
            loading={remove.isPending}
            disabled={!confirmed || scope.isFetching}
            onClick={() => data && remove.mutate(data.key)}
          >
            Eliminar pieza
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
