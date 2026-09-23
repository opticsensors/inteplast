import { Link } from "@tanstack/react-router"
import {
  Check,
  ChevronDown,
  Download,
  FolderOpen,
  Loader2,
  Plus,
  Star,
  Trash2,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { FileLink } from "@/components/Common/FileLink"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { pickNativePath } from "@/lib/nativePicker"
import { cn } from "@/lib/utils"
import { formatFileSize } from "@/utils"
import {
  canBePrimary,
  FILE_ICONS,
  FILE_KINDS,
  FILE_LABELS,
  type FileDraft,
  guessFileKind,
  newFileKey,
  normalizePrimaries,
  PRIMARY_KINDS,
} from "./pieceFileDrafts"

export function PartFiles({
  files,
  folder,
  partId,
  editing,
  disabled,
  onChange,
  onPickingChange,
}: {
  files: FileDraft[]
  folder: string
  partId?: string
  editing: boolean
  disabled: boolean
  onChange: (files: FileDraft[]) => void
  onPickingChange: (value: boolean) => void
}) {
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState("")
  const focus = useRef<string | undefined>(undefined)
  const picker = useRef<AbortController | null>(null)
  useEffect(() => () => picker.current?.abort(), [])
  const choose = async (current?: FileDraft, kind?: FileDraft["kind"]) => {
    const controller = new AbortController()
    picker.current = controller
    setBusy(current?.key ?? "new")
    onPickingChange(true)
    setError("")
    try {
      const path = await pickNativePath("file", controller.signal)
      if (!path || controller.signal.aborted) return
      if (!folder || !path.startsWith(`${folder}/`))
        throw new Error(
          "Selecciona un archivo dentro de la carpeta de esta pieza.",
        )
      if (
        files.some(
          (file) =>
            (file.path ?? file.originalPath) === path &&
            file.key !== current?.key,
        )
      )
        throw new Error("Este fichero ya está añadido.")
      const filename = path.split("/").pop()!
      const draft: FileDraft = current
        ? {
            ...current,
            path,
            file_id: undefined,
            file: undefined,
            originalPath: undefined,
            source_version: null,
            name:
              current.name ===
              (current.file?.filename ?? current.path?.split("/").pop())
                ? filename
                : current.name,
          }
        : {
            key: newFileKey(),
            path,
            kind: kind ?? guessFileKind(path),
            name: filename,
            primary: false,
          }
      if (!current) focus.current = draft.key
      onChange(
        normalizePrimaries(
          current
            ? files.map((file) => (file.key === current.key ? draft : file))
            : [...files, draft],
        ),
      )
    } catch (error) {
      if (!controller.signal.aborted) setError(fileErrorMessage(error))
    } finally {
      picker.current = null
      setBusy(null)
      onPickingChange(false)
    }
  }
  const locked = disabled || busy !== null
  return (
    <div className="space-y-2">
      {files.map((file) => {
        const Icon = FILE_ICONS[file.kind]
        const label = FILE_LABELS[file.kind]
        const multiple =
          canBePrimary(file.kind) &&
          files.filter((other) => other.kind === file.kind).length > 1
        return (
          <fieldset
            key={file.key}
            disabled={locked}
            aria-label={`Fichero ${file.name}`}
            className="flex min-w-0 items-center gap-1 rounded-md border px-1.5 py-1.5 text-sm"
          >
            {editing ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 shrink-0 gap-0.5 px-1 text-muted-foreground"
                    title="Cambiar el tipo"
                    aria-label={`Tipo de ${file.name}: ${label}`}
                    disabled={locked}
                  >
                    <Icon className="size-5" />
                    <ChevronDown className="size-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  {FILE_KINDS.map((kind) => {
                    const KindIcon = FILE_ICONS[kind]
                    return (
                      <DropdownMenuItem
                        key={kind}
                        onSelect={() =>
                          onChange(
                            normalizePrimaries(
                              files.map((row) =>
                                row.key === file.key
                                  ? { ...row, kind, primary: false }
                                  : row,
                              ),
                            ),
                          )
                        }
                      >
                        <KindIcon />
                        {FILE_LABELS[kind]}
                        {kind === file.kind && (
                          <Check className="ml-auto size-3.5" />
                        )}
                      </DropdownMenuItem>
                    )
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <span className="flex size-8 shrink-0 items-center justify-center text-muted-foreground">
                <Icon className="size-5" />
              </span>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 items-center gap-2 px-1 leading-5">
                <p className="truncate font-medium">{label}</p>
                {!editing && file.primary && multiple && (
                  <Star
                    className="size-3 shrink-0 fill-primary text-primary"
                    aria-label="Archivo principal"
                  />
                )}
              </div>
              {editing ? (
                <Input
                  ref={(element) => {
                    if (element && focus.current === file.key) {
                      element.focus()
                      element.select()
                      focus.current = undefined
                    }
                  }}
                  value={file.name}
                  aria-label={`Nombre de ${file.file?.filename ?? file.path?.split("/").pop() ?? label}`}
                  title={file.name}
                  maxLength={255}
                  onChange={(event) =>
                    onChange(
                      files.map((row) =>
                        row.key === file.key
                          ? { ...row, name: event.target.value }
                          : row,
                      ),
                    )
                  }
                  className={cn(
                    "h-5 min-w-0 overflow-hidden text-ellipsis border-0 px-1 py-0 text-xs shadow-none focus-visible:ring-1 md:text-xs",
                    !file.name.trim() && "ring-1 ring-destructive",
                  )}
                />
              ) : file.file && partId ? (
                <Link
                  to="/parts/$partId/fichero/$fileId"
                  params={{ partId, fileId: file.file.id }}
                  title={file.name}
                  className="block truncate px-1 text-xs leading-4 text-muted-foreground hover:underline"
                >
                  {file.name}
                </Link>
              ) : (
                <p
                  className="truncate px-1 text-xs leading-4"
                  title={file.name}
                >
                  {file.name}
                </p>
              )}
            </div>
            {file.file && (
              <span className="shrink-0 self-center px-1 text-xs tabular-nums text-muted-foreground">
                {formatFileSize(file.file.size)}
              </span>
            )}
            {editing ? (
              <>
                {multiple && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-7 shrink-0"
                    title={
                      file.primary ? "Archivo principal" : "Usar como principal"
                    }
                    aria-label={`Usar ${file.name} como principal`}
                    aria-pressed={file.primary}
                    onClick={() =>
                      onChange(
                        files.map((row) =>
                          row.kind === file.kind
                            ? { ...row, primary: row.key === file.key }
                            : row,
                        ),
                      )
                    }
                  >
                    <Star
                      className={cn(
                        "size-3.5",
                        file.primary && "fill-primary text-primary",
                      )}
                    />
                  </Button>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="size-7 shrink-0"
                  disabled={locked || !folder}
                  title={`Cambiar ${file.name}`}
                  aria-label={`Cambiar ${file.name}`}
                  onClick={() => void choose(file)}
                >
                  {busy === file.key ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <FolderOpen className="size-3.5" />
                  )}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-7 shrink-0 text-destructive"
                  title={`Quitar ${file.name}`}
                  aria-label={`Quitar ${file.name}`}
                  onClick={() =>
                    onChange(
                      normalizePrimaries(
                        files.filter((row) => row.key !== file.key),
                      ),
                    )
                  }
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </>
            ) : (
              file.file && (
                <Button
                  asChild
                  variant="outline"
                  size="icon"
                  className="size-7 shrink-0"
                >
                  <FileLink
                    fileId={file.file.id}
                    downloadFile
                    title={`Descargar ${file.name}`}
                  >
                    <Download className="size-3.5" />
                    <span className="sr-only">Descargar {file.name}</span>
                  </FileLink>
                </Button>
              )
            )}
          </fieldset>
        )
      })}
      {editing &&
        PRIMARY_KINDS.filter(
          (kind) => !files.some((file) => file.kind === kind),
        ).map((kind) => {
          const Icon = FILE_ICONS[kind]
          return (
            <div
              key={kind}
              className="flex min-w-0 items-center gap-2 rounded-md border px-2 py-1.5 text-sm"
            >
              <Icon className="size-5 shrink-0 text-muted-foreground" />
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <p className="shrink-0 font-medium">{FILE_LABELS[kind]}</p>
                <p className="truncate text-xs text-muted-foreground">
                  Sin archivo
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="size-7 shrink-0"
                aria-label={`Añadir ${FILE_LABELS[kind]}`}
                disabled={locked || !folder}
                onClick={() => void choose(undefined, kind)}
              >
                <FolderOpen className="size-3.5" />
              </Button>
            </div>
          )
        })}
      {!files.length && !editing && (
        <p className="text-sm text-muted-foreground">Sin archivos añadidos.</p>
      )}
      {editing && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={locked || !folder}
          onClick={() => void choose()}
        >
          {busy === "new" ? (
            <Loader2 className="mr-1 size-3.5 animate-spin" />
          ) : (
            <Plus className="mr-1 size-3.5" />
          )}
          Añadir fichero
        </Button>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
