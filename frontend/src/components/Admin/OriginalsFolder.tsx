import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FolderOpen } from "lucide-react"
import { useState } from "react"

import { ApiError, OriginalsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { useLoginMethods } from "@/hooks/useLoginMethods"

const queryKey = ["originals-folder"]

function errorMessage(error: Error) {
  const body = error instanceof ApiError ? error.body : null
  const detail =
    body && typeof body === "object" && "detail" in body ? body.detail : null
  return typeof detail === "string"
    ? detail
    : "No se ha podido completar la operación. Vuelve a intentarlo."
}

function FolderForm({ onSaved }: { onSaved: () => void }) {
  const [link, setLink] = useState("")
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const check = useMutation({
    mutationFn: (url: string) =>
      OriginalsService.checkOriginals({ requestBody: { url } }),
  })
  const save = useMutation({
    mutationFn: (ticket: string) =>
      OriginalsService.saveOriginals({ requestBody: { ticket } }),
    onSuccess: (folder) => {
      queryClient.setQueryData(queryKey, folder)
      void queryClient.invalidateQueries()
      showSuccessToast("Carpeta de originales guardada")
      onSaved()
    },
  })
  const result = check.data
  const error = check.error ?? save.error
  const busy = check.isPending || save.isPending
  return (
    <form
      className="grid gap-4"
      onSubmit={(event) => {
        event.preventDefault()
        if (busy || !link.trim()) return
        save.reset()
        check.mutate(link.trim())
      }}
    >
      <div className="grid gap-2">
        <Label htmlFor="originals-folder-url">Cambiar enlace carpeta:</Label>
        <Input
          id="originals-folder-url"
          type="url"
          required
          autoComplete="off"
          placeholder="Pega aquí el enlace de SharePoint"
          value={link}
          disabled={busy}
          onChange={(event) => {
            setLink(event.target.value)
            check.reset()
            save.reset()
          }}
        />
      </div>
      {check.isPending && (
        <output className="text-sm text-muted-foreground">
          Comprobando las carpetas de pieza…
        </output>
      )}
      {result && (
        <div
          className="grid min-w-0 gap-2 rounded-md border p-3 text-sm"
          aria-live="polite"
        >
          <strong>{result.folder.name}</strong>
          <p>
            Carpeta accesible
            {result.checked === 0
              ? ". El catálogo aún no tiene carpetas de pieza vinculadas."
              : ` · ${result.found} de ${result.checked} ${result.checked === 1 ? "carpeta de pieza encontrada" : "carpetas de pieza encontradas"}`}
          </p>
          {result.unavailable.length > 0 && (
            <div>
              <p>Carpetas no disponibles</p>
              <ul className="grid gap-1 break-all text-muted-foreground">
                {result.unavailable.map((path) => (
                  <li key={path}>{path}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {errorMessage(error)}
        </p>
      )}
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline" disabled={save.isPending}>
            Cancelar
          </Button>
        </DialogClose>
        <Button type="submit" variant="outline" disabled={busy || !link.trim()}>
          Comprobar
        </Button>
        <Button
          type="button"
          disabled={busy || !result || save.isError}
          onClick={() => {
            if (result) save.mutate(result.ticket)
          }}
        >
          {save.isPending ? "Guardando…" : "Guardar"}
        </Button>
      </DialogFooter>
    </form>
  )
}

export default function OriginalsFolder() {
  const [open, setOpen] = useState(false)
  const { data: methods } = useLoginMethods()
  const folder = useQuery({
    queryKey,
    queryFn: () => OriginalsService.readOriginals(),
    enabled: open && !!methods?.sharepoint,
  })
  if (!methods?.sharepoint) return null
  const current = folder.data
  const name = current?.name.split("/").filter(Boolean).pop()
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="h-11">
          <FolderOpen /> SharePoint
        </Button>
      </DialogTrigger>
      <DialogContent closeLabel="Cerrar">
        <DialogHeader>
          <DialogTitle>Añadir SharePoint</DialogTitle>
          <DialogDescription>
            Cambia aquí el enlace de SharePoint que usa el catálogo.
          </DialogDescription>
        </DialogHeader>
        {current && (
          <div className="grid min-w-0 gap-2">
            <Label asChild>
              <span>Carpeta actual</span>
            </Label>
            {current.web_url ? (
              <Button
                asChild
                variant="outline"
                className="w-full min-w-0 justify-start border-input px-3 font-normal"
              >
                <a
                  href={current.web_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Abrir ${name} en SharePoint`}
                  title={current.web_url}
                >
                  <span className="truncate underline underline-offset-2">
                    {current.web_url}
                  </span>
                </a>
              </Button>
            ) : (
              <span className="flex h-9 items-center rounded-md border border-input px-3 text-sm text-muted-foreground">
                {name}
              </span>
            )}
          </div>
        )}
        {folder.isError && (
          <p role="alert" className="text-sm text-destructive">
            {errorMessage(folder.error)}
          </p>
        )}
        {open && <FolderForm onSaved={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}
