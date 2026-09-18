import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useRef } from "react"

import { type PartPublic, PartsService, type PartUpdate } from "@/client"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import { PartFolderPicker } from "./PartFolderPicker"
import { SaveStatus } from "./SaveStatus"
import { useAutosave } from "./useAutosave"

export function PartIdentityEditor({
  part,
  isNew,
}: {
  part: PartPublic
  isNew: boolean
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isNew) nameRef.current?.select()
  }, [isNew])

  const update = useMutation({
    mutationFn: (requestBody: PartUpdate) =>
      PartsService.updatePart({ partId: part.id, requestBody }),
    onError: handleError.bind(showErrorToast),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parts"] })
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })
  const server = useMemo(
    () => ({ code: part.code, name: part.name ?? "" }),
    [part.code, part.name],
  )
  const autosave = useAutosave(
    server,
    (patch) =>
      update.mutateAsync({
        ...(patch.code !== undefined ? { code: patch.code.trim() } : {}),
        ...(patch.name !== undefined
          ? { name: patch.name.trim() || null }
          : {}),
      }),
    (values) => Boolean(values.code.trim()),
  )

  return (
    <div className="min-w-0 flex-1">
      <div className="flex items-center gap-1">
        <div className="flex min-w-0 flex-1 flex-wrap gap-1">
          <Input
            value={autosave.values.code}
            onChange={(event) => autosave.change({ code: event.target.value })}
            aria-label="Codigo de la pieza"
            placeholder="Codigo de la pieza"
            maxLength={64}
            className={cn(
              "h-8 w-28 border-0 px-2 font-mono text-sm font-semibold shadow-none focus-visible:ring-1",
              !autosave.values.code.trim() && "ring-1 ring-destructive",
            )}
          />
          <Input
            ref={nameRef}
            value={autosave.values.name}
            onChange={(event) => autosave.change({ name: event.target.value })}
            aria-label="Nombre de la pieza"
            placeholder="Nombre de la pieza"
            maxLength={255}
            className="h-8 min-w-28 flex-1 border-0 px-2 text-sm shadow-none focus-visible:ring-1"
          />
        </div>
        <PartFolderPicker
          path={part.folder_path}
          onSelected={async (folderPath) => {
            if (!(await autosave.flush()))
              throw new Error(
                "Guarda el nombre o codigo antes de cambiar la carpeta.",
              )
            await update.mutateAsync({ folder_path: folderPath })
          }}
        />
      </div>
      <SaveStatus
        error={autosave.error}
        saving={autosave.saving}
        retry={autosave.flush}
      />
    </div>
  )
}
