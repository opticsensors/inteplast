import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Download,
  FolderClock,
  FolderOpen,
  ImageIcon,
  Pencil,
} from "lucide-react"
import { type ReactNode, useState } from "react"
import { type FilePublic, FilesService } from "@/client"
import { FileLink } from "@/components/Common/FileLink"
import { FileUpload } from "@/components/Common/FileUpload"
import { Button } from "@/components/ui/button"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"

const folders = {
  drawing: [
    { label: "Carpeta del plano en SharePoint", icon: FolderOpen },
    { label: "Histórico de planos en SharePoint", icon: FolderClock },
  ],
}

export function SharePointFolders({ kind }: { kind: keyof typeof folders }) {
  return (
    <div className="flex items-center gap-1">
      {folders[kind].map(({ label, icon: Icon }) => (
        <Button
          key={label}
          type="button"
          size="icon"
          variant="ghost"
          aria-disabled="true"
          aria-label={label}
          title={label}
          className="cursor-default text-muted-foreground opacity-60 hover:bg-transparent hover:text-muted-foreground"
        >
          <Icon aria-hidden="true" className="size-5" />
        </Button>
      ))}
    </div>
  )
}

type AttachmentKind = "mold" | "moldflow"

export function isFolderAttachment(kind?: string): kind is AttachmentKind {
  return kind === "mold" || kind === "moldflow"
}

const kindNames = { mold: "Molde", moldflow: "Moldflow" }
const previewFrame = "h-[70vh] w-full overflow-hidden rounded-lg bg-muted/30"

export function AttachmentFolder({
  kind,
  partId,
  fileId,
  fileVersion,
  folderOnly = false,
}: {
  kind: AttachmentKind
  partId?: string
  fileId?: string
  fileVersion?: string | null
  folderOnly?: boolean
}) {
  const folder = useQuery({
    queryKey: ["attachment-folder", kind, partId, fileId, fileVersion],
    queryFn: () => FilesService.readAttachmentFolder({ kind, partId, fileId }),
    enabled: Boolean(partId || fileId),
    staleTime: 60_000,
    retry: false,
  })
  const name = kindNames[kind]
  const label = `Carpeta de ${name} en SharePoint`
  if (folderOnly && !folder.data) return null
  if (!folder.data) {
    return (
      <Button
        type="button"
        size="icon"
        variant="ghost"
        disabled
        aria-label={label}
        title={folder.error ? fileErrorMessage(folder.error) : label}
      >
        <FolderOpen />
      </Button>
    )
  }
  return (
    <Button
      asChild
      type="button"
      size={folderOnly ? "sm" : "icon"}
      variant="outline"
    >
      <a
        href={folder.data}
        target="_blank"
        rel="noopener noreferrer"
        title={label}
        aria-label={label}
      >
        <FolderOpen aria-hidden="true" />
        {folderOnly && name}
      </a>
    </Button>
  )
}

export function AttachmentDetail({
  kind,
  file,
  partId,
  name,
  context,
  sourcePicker,
}: {
  kind: AttachmentKind
  file: FilePublic
  partId?: string
  name: string
  context?: string
  sourcePicker?: ReactNode
}) {
  const client = useQueryClient()
  const key = ["attachment-screenshot", file.id, file.version]
  const saved = useQuery({
    queryKey: key,
    queryFn: () => FilesService.readAttachmentScreenshot({ fileId: file.id }),
    retry: false,
  })
  const preview = useFileAccess(saved.data?.id)
  const [edit, setEdit] = useState<{
    previous: string | null
    image: FilePublic | null
  } | null>(null)
  const [upload, setUpload] = useState({ pending: false, error: false })
  const save = useMutation({
    mutationFn: (draft: NonNullable<typeof edit>) =>
      FilesService.updateAttachmentScreenshot({
        fileId: file.id,
        requestBody: {
          image_id: draft.image?.id ?? null,
          previous_id: draft.previous,
        },
      }),
    onSuccess: (image) => {
      client.setQueryData(key, image)
      setEdit(null)
    },
    onError: () => void saved.refetch(),
  })
  const download = `Descargar original de ${kindNames[kind]}`
  // Reading and editing captures both require an active user with access to the original.
  const canEdit = saved.isSuccess
  return (
    <section className="space-y-4">
      {context && <p className="text-sm text-muted-foreground">{context}</p>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="break-words text-2xl font-bold tracking-tight">
            {name}
          </h1>
          {name !== file.filename && (
            <p className="break-words text-sm text-muted-foreground">
              {file.filename}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {(edit || saved.isError) && sourcePicker}
          <AttachmentFolder
            kind={kind}
            partId={partId}
            fileId={file.id}
            fileVersion={file.version}
          />
          <Button asChild variant="outline" size="icon">
            <FileLink
              fileId={file.id}
              downloadFile
              download={file.filename}
              aria-label={download}
              title={download}
            >
              <Download aria-hidden="true" />
            </FileLink>
          </Button>
          {!edit && canEdit && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              title="Editar captura"
              aria-label="Editar captura"
              onClick={() => {
                save.reset()
                setUpload({ pending: false, error: false })
                setEdit({
                  previous: saved.data?.id ?? null,
                  image: saved.data ?? null,
                })
              }}
            >
              <Pencil />
            </Button>
          )}
        </div>
      </div>
      {saved.isError && (
        <p role="alert">
          {fileErrorMessage(saved.error)}{" "}
          <Button size="sm" variant="link" onClick={() => void saved.refetch()}>
            Reintentar
          </Button>
        </p>
      )}
      {edit && canEdit ? (
        <fieldset className="min-w-0 space-y-3" disabled={save.isPending}>
          <FileUpload
            variant="image"
            imagePrompt="Arrastra una captura, pégala con Ctrl+V o haz clic para elegirla"
            value={edit.image}
            onChange={(image) => setEdit({ ...edit, image })}
            onUploadStateChange={setUpload}
            boxClassName={previewFrame}
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={upload.pending}
              onClick={() => setEdit(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={upload.pending || upload.error}
              onClick={() => save.mutate(edit)}
            >
              Guardar captura
            </Button>
          </div>
          {save.error && <p role="alert">{fileErrorMessage(save.error)}</p>}
        </fieldset>
      ) : (
        <div
          className={`${previewFrame} flex items-center justify-center border`}
        >
          {saved.isSuccess && saved.data && preview.url ? (
            <img
              src={preview.url}
              alt={`Captura de ${name}`}
              className="size-full object-contain"
            />
          ) : (
            <ImageIcon
              aria-label={`Vista previa de ${kindNames[kind]}`}
              role="img"
              className="size-8 text-muted-foreground"
            />
          )}
        </div>
      )}
    </section>
  )
}
