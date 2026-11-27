import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { FolderClock, FolderOpen, Pencil } from "lucide-react"
import type { ReactNode } from "react"
import {
  type FilePublic,
  type FilesReadAttachmentFolderData,
  FilesService,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { fileErrorMessage } from "@/hooks/useFileAccess"

export const galleryLabels = {
  mold: "Molde",
  moldflow: "Moldflow",
  scan: "Pieza real",
} as const
export type AttachmentKind = keyof typeof galleryLabels
export function isFolderAttachment(kind?: string): kind is AttachmentKind {
  return kind === "mold" || kind === "moldflow" || kind === "scan"
}

const editStyle = "border-primary text-primary hover:text-primary"
export function EditGalleryButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      className={editStyle}
      title="Editar galería"
      aria-label="Editar galería"
      onClick={onClick}
    >
      <Pencil />
    </Button>
  )
}

export function EditAttachmentLink({ partId }: { partId: string }) {
  const label = "Editar archivos de la pieza"
  return (
    <Button asChild variant="outline" size="icon" className={editStyle}>
      <Link
        to="/parts/$partId"
        params={{ partId }}
        search={{ editar: true }}
        hash="archivos"
        title={label}
        aria-label={label}
      >
        <Pencil />
      </Link>
    </Button>
  )
}

export function AttachmentHeader({
  kind,
  file,
  partId,
  context,
  title,
  subtitle,
  children,
}: {
  kind: FilesReadAttachmentFolderData["kind"]
  file?: FilePublic | null
  partId?: string
  context?: string
  title: string
  subtitle?: string
  children?: ReactNode
}) {
  const params = { kind, partId, fileId: file?.id }
  const key = [kind, partId, file?.id, file?.version]
  const current = useQuery({
    queryKey: ["attachment-folder", ...key],
    queryFn: () => FilesService.readAttachmentFolder(params),
    staleTime: 60_000,
    retry: false,
  })
  const history = useQuery({
    queryKey: ["attachment-history", ...key],
    enabled: Boolean(current.data && !current.isError),
    queryFn: () => FilesService.readAttachmentHistory(params),
    staleTime: 60_000,
    retry: false,
  })
  const archives =
    current.data && !current.isError && !history.isError
      ? (history.data ?? [])
      : []
  const folderLabel = "Abrir carpeta en SharePoint"
  const historyLabel = "Abrir histórico en SharePoint"
  return (
    <header className="space-y-1">
      {context && <p className="text-sm text-muted-foreground">{context}</p>}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="break-words text-2xl font-bold tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="break-words text-sm text-muted-foreground">
              {subtitle}
            </p>
          )}
        </div>
        <fieldset
          aria-label="Acciones del adjunto"
          className="ml-auto flex shrink-0 items-center gap-2"
        >
          {current.data && !current.isError ? (
            <Button asChild size="icon" variant="outline">
              <a
                href={current.data}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={folderLabel}
                title={folderLabel}
              >
                <FolderOpen />
              </a>
            </Button>
          ) : (
            <Button
              disabled
              variant="outline"
              size="icon"
              aria-label={folderLabel}
              title={
                current.error
                  ? fileErrorMessage(current.error)
                  : "Carpeta de SharePoint no disponible"
              }
            >
              <FolderOpen />
            </Button>
          )}
          {archives.length === 1 && (
            <Button asChild size="icon" variant="outline">
              <a
                href={archives[0].url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={historyLabel}
                title={historyLabel}
              >
                <FolderClock />
              </a>
            </Button>
          )}
          {archives.length > 1 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  title={historyLabel}
                  aria-label={historyLabel}
                >
                  <FolderClock />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {archives.map((folder) => (
                  <DropdownMenuItem key={folder.url} asChild>
                    <a
                      href={folder.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {folder.name}
                    </a>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          {children}
        </fieldset>
      </div>
    </header>
  )
}
