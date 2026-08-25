import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, ChevronDown, Loader2, Trash2, Upload } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import {
  type AssetKind,
  type FeatureAssetPublic,
  type FeatureAssetUpdate,
  FeaturesService,
  FilesService,
  type PartPublic,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import useDebounce from "@/hooks/useDebounce"
import { cn } from "@/lib/utils"
import { formatFileSize, handleError } from "@/utils"
import { ASSET_ICONS, ASSET_KIND_LABELS, ASSET_KINDS } from "./constants"

/** Nombre con el que nace una fila. Si sigue asi, el fichero lo reemplaza. */
export const NEW_ASSET_NAME = "Nuevo fichero"

const AUTOSAVE_MS = 700

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
 * - **el tipo y la pieza**, en el desplegable que abre el icono,
 * - **el nombre**, escribiendo encima,
 * - **el fichero**, con *Subir* / *Cambiar*.
 *
 * 🔑 No hay boton de editar ni modal. Y se guarda solo, como las notas: lo
 * unico que se guarda a mano en esta pagina es la cabecera del feature.
 */
export function AssetEditRow({
  asset,
  parts,
  isNew,
}: {
  asset: FeatureAssetPublic
  /** Para poder mover el fichero a otra pieza desde el mismo desplegable. */
  parts: PartPublic[]
  isNew: boolean
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const [name, setName] = useState(asset.name)
  const nameRef = useRef<HTMLInputElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

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
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })
  const { mutate: save } = update

  const remove = useMutation({
    mutationFn: () => FeaturesService.deleteFeatureAsset({ assetId: asset.id }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const upload = useMutation({
    mutationFn: (file: File) => FilesService.uploadFile({ formData: { file } }),
    onSuccess: (uploaded) => {
      const patch: FeatureAssetUpdate = { file_id: uploaded.id }
      // Fila recien creada y sin tocar: la rellena el propio fichero.
      if (name === NEW_ASSET_NAME) {
        const base = uploaded.filename.replace(/\.[^.]+$/, "")
        patch.name = base
        setName(base)
        const guessed = KIND_BY_EXTENSION[extensionOf(uploaded.filename)]
        if (guessed) patch.kind = guessed
      }
      save(patch)
    },
    onError: handleError.bind(showErrorToast),
  })

  const debouncedName = useDebounce(name, AUTOSAVE_MS)
  useEffect(() => {
    const clean = debouncedName.trim()
    if (clean && clean !== asset.name) save({ name: clean })
  }, [debouncedName, asset.name, save])

  const Icon = ASSET_ICONS[asset.kind]
  const file = asset.file

  return (
    <div className="flex items-center gap-1 rounded-md border px-1 py-1 text-sm">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 shrink-0 justify-start gap-1 px-1.5 font-normal text-muted-foreground"
            title="Cambiar el tipo o la pieza"
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
                {kind === asset.kind && <Check className="ml-auto size-3.5" />}
              </DropdownMenuItem>
            )
          })}
          {parts.length > 0 && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Pieza</DropdownMenuLabel>
              {parts.map((part) => (
                <DropdownMenuItem
                  key={part.id}
                  onSelect={() =>
                    part.id !== asset.part?.id && save({ part_id: part.id })
                  }
                >
                  <span className="font-mono">{part.code}</span>
                  <span className="truncate text-muted-foreground">
                    {part.name}
                  </span>
                  {part.id === asset.part?.id && (
                    <Check className="ml-auto size-3.5" />
                  )}
                </DropdownMenuItem>
              ))}
              <DropdownMenuItem
                onSelect={() => asset.part && save({ part_id: null })}
              >
                Sin pieza
                {!asset.part && <Check className="ml-auto size-3.5" />}
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Input
        ref={nameRef}
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Nombre del fichero"
        className={cn(
          "h-7 min-w-0 flex-1 border-0 px-2 shadow-none focus-visible:ring-1",
          !name.trim() && "ring-1 ring-destructive",
        )}
      />

      {file ? (
        <>
          <span
            className="hidden shrink-0 text-xs text-muted-foreground sm:inline"
            title={file.filename}
          >
            {file.filename} · {formatFileSize(file.size)}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            title="Cambiar el fichero"
            onClick={() => fileRef.current?.click()}
            disabled={upload.isPending}
          >
            {upload.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Upload className="size-3.5" />
            )}
            <span className="sr-only">Cambiar el fichero de {asset.name}</span>
          </Button>
        </>
      ) : (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 shrink-0"
          onClick={() => fileRef.current?.click()}
          disabled={upload.isPending}
        >
          {upload.isPending ? (
            <Loader2 className="mr-1 size-3.5 animate-spin" />
          ) : (
            <Upload className="mr-1 size-3.5" />
          )}
          Subir
        </Button>
      )}

      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-7 shrink-0 text-destructive"
        onClick={() => remove.mutate()}
        disabled={remove.isPending}
      >
        <Trash2 className="size-3.5" />
        <span className="sr-only">Borrar {asset.name}</span>
      </Button>

      <input
        ref={fileRef}
        type="file"
        className="hidden"
        onChange={(event) => {
          const chosen = event.target.files?.[0]
          if (chosen) upload.mutate(chosen)
          event.target.value = ""
        }}
      />
    </div>
  )
}
