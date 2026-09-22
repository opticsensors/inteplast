import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, ChevronDown, Download, Trash2 } from "lucide-react"
import { type ReactNode, useEffect, useMemo, useRef } from "react"

import {
  type AssetKind,
  type FeatureAssetPublic,
  type FeatureAssetUpdate,
  FeaturesService,
} from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { formatFileSize, handleError } from "@/utils"
import { ASSET_ICONS, ASSET_KIND_LABELS, ASSET_KINDS } from "./constants"
import { DocumentStatus } from "./DocumentStatus"
import { assetName } from "./parts"
import { SaveStatus } from "./SaveStatus"
import { SourceFilePicker } from "./SourceFilePicker"
import { useAutosave } from "./useAutosave"
import { usePendingTask } from "./usePendingTask"

/** Nombre con el que nace una fila. Si sigue asi, el fichero lo reemplaza. */
export const NEW_ASSET_NAME = "Nuevo fichero"

/**
 * Tipo deducido de la extension. `step`, `stp` e `igs` **no estan**: pueden ser
 * el molde o la pieza, y adivinar mal es peor que no adivinar.
 */
const KIND_BY_EXTENSION: Record<string, AssetKind> = {
  pdf: "drawing",
  stl: "scan",
  ply: "scan",
  obj: "scan",
  glb: "scan",
  gltf: "scan",
  mfr: "moldflow",
  mpi: "moldflow",
}

const extensionOf = (filename: string) =>
  filename.slice(filename.lastIndexOf(".") + 1).toLowerCase()

/**
 * Un fichero de una pieza, en modo edicion. Todo se cambia en la propia fila:
 *
 * - **el tipo**, en el desplegable que abre el icono,
 * - **el nombre**, escribiendo encima,
 * - **el fichero**, con el selector de Windows para vincular el original.
 *
 * 🔑 No hay boton de editar ni modal. Y se guarda solo, como las notas: lo
 * unico que se guarda a mano en esta pagina es la cabecera del feature.
 */
export function AssetEditRow({
  asset,
  isNew,
  dragHandle,
}: {
  asset: FeatureAssetPublic
  isNew: boolean
  dragHandle?: ReactNode
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isNew) nameRef.current?.select()
  }, [isNew])

  const update = useMutation({
    mutationFn: (data: FeatureAssetUpdate) =>
      FeaturesService.updateFeatureAsset({
        assetId: asset.id,
        requestBody: data,
      }),
    onError: handleError.bind(showErrorToast),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["features"] }),
  })
  const filename = assetName(asset)
  const server = useMemo(() => ({ name: filename }), [filename])
  const autosave = useAutosave(
    server,
    (patch) => update.mutateAsync(patch),
    (values) => Boolean(values.name.trim()),
  )
  const { name } = autosave.values
  const metadata = usePendingTask(async (patch: FeatureAssetUpdate) => {
    if (!(await autosave.flush())) throw new Error("Nombre sin guardar")
    await update.mutateAsync(patch)
  })
  const save = (patch: FeatureAssetUpdate) => {
    void metadata.run(patch)
  }

  const remove = useMutation({
    mutationFn: () => FeaturesService.deleteFeatureAsset({ assetId: asset.id }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const Icon = ASSET_ICONS[asset.kind]
  const file = asset.file

  return (
    <div>
      <div className="flex items-center gap-1 rounded-md border px-1 py-1 text-sm">
        {dragHandle}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 shrink-0 justify-start gap-1 px-1.5 font-normal text-muted-foreground"
              title="Cambiar el tipo"
              disabled={metadata.pending}
            >
              <Icon className="size-3.5" />
              <span className="hidden sm:inline">
                {ASSET_KIND_LABELS[asset.kind]}
              </span>
              <ChevronDown className="size-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuLabel>Tipo</DropdownMenuLabel>
            {ASSET_KINDS.map((kind) => {
              const KindIcon = ASSET_ICONS[kind]
              return (
                <DropdownMenuItem
                  key={kind}
                  onSelect={() => kind !== asset.kind && save({ kind })}
                >
                  <KindIcon />
                  {ASSET_KIND_LABELS[kind]}
                  {kind === asset.kind && (
                    <Check className="ml-auto size-3.5" />
                  )}
                </DropdownMenuItem>
              )
            })}
          </DropdownMenuContent>
        </DropdownMenu>

        <Input
          ref={nameRef}
          value={asset.file?.filename ?? name}
          readOnly={Boolean(asset.file)}
          title={asset.file?.filename}
          disabled={metadata.pending}
          onChange={(event) => autosave.change({ name: event.target.value })}
          placeholder="Nombre del fichero"
          className={cn(
            "h-7 min-w-0 flex-1 border-0 px-2 shadow-none focus-visible:ring-1",
            !name.trim() && "ring-1 ring-destructive",
          )}
        />

        {file && (
          <span className="shrink-0 text-xs text-muted-foreground">
            {formatFileSize(file.size)}
          </span>
        )}
        {file && (
          <Button
            asChild
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            title={`Descargar ${filename}`}
          >
            <FileLink fileId={file.id} downloadFile download={file.filename}>
              <Download className="size-3.5" />
              <span className="sr-only">Descargar {filename}</span>
            </FileLink>
          </Button>
        )}
        <SourceFilePicker
          initialPath={asset.part?.folder_path ?? ""}
          compact
          document={file ?? undefined}
          disabled={metadata.pending}
          onLinked={async (linked) => {
            const patch: FeatureAssetUpdate = {
              file_id: linked.id,
              name: linked.filename,
            }
            if (name === NEW_ASSET_NAME) {
              const guessed = KIND_BY_EXTENSION[extensionOf(linked.filename)]
              if (guessed) patch.kind = guessed
            }
            autosave.change({ name: linked.filename })
            if (!(await metadata.run(patch)))
              throw new Error(
                "No se ha podido guardar el adjunto. Reintenta el guardado de la fila.",
              )
          }}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-7 shrink-0 text-destructive"
          onClick={() => remove.mutate()}
          disabled={remove.isPending || metadata.pending || autosave.saving}
        >
          <Trash2 className="size-3.5" />
          <span className="sr-only">Borrar {filename}</span>
        </Button>
      </div>
      <DocumentStatus file={file} />
      <SaveStatus
        error={autosave.error}
        saving={autosave.saving}
        retry={autosave.flush}
      />
      <SaveStatus
        error={metadata.error}
        saving={metadata.pending}
        retry={metadata.retry}
      />
    </div>
  )
}
