import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ImageIcon, Plus, X } from "lucide-react"
import { type ReactNode, useCallback, useEffect, useRef, useState } from "react"
import { type FilePublic, FilesService } from "@/client"
import {
  IMAGE_UPLOAD_ACCEPT,
  isPreviewableImage,
} from "@/components/Features/viewers"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"
import {
  AttachmentHeader,
  type AttachmentKind,
  EditGalleryButton,
  galleryLabels,
} from "./AttachmentActions"

const capacity = 8
type Photo = FilePublic | File
type Draft = {
  previous: string[]
  photos: Photo[]
  initialIndex: number
  addingPhotos: boolean
}
function photoName(photo: Photo) {
  return photo instanceof File ? photo.name : photo.filename
}

function GalleryImage({
  photo,
  expanded = false,
}: {
  photo: Photo
  expanded?: boolean
}) {
  const remote = useFileAccess(photo instanceof File ? undefined : photo.id)
  const [preview, setPreview] = useState<{ file: File; url: string }>()
  useEffect(() => {
    if (!(photo instanceof File)) return
    const url = URL.createObjectURL(photo)
    setPreview({ file: photo, url })
    return () => URL.revokeObjectURL(url)
  }, [photo])
  const src =
    photo instanceof File
      ? preview?.file === photo
        ? preview.url
        : undefined
      : remote.url
  return src ? (
    <img
      src={src}
      alt={photoName(photo)}
      className={
        expanded
          ? "mx-auto max-h-[80vh] max-w-full object-contain"
          : "size-full object-contain"
      }
    />
  ) : (
    <span className="text-sm text-muted-foreground">
      {remote.isError ? "Imagen no disponible" : "Cargando…"}
    </span>
  )
}

export function AttachmentDetail({
  kind,
  partId,
  file,
  context,
  sourcePicker,
}: {
  kind: AttachmentKind
  partId?: string
  file?: FilePublic | null
  context?: string
  sourcePicker?: ReactNode
}) {
  const fileId = file?.id
  const client = useQueryClient()
  const key = ["attachment-gallery", kind, partId || fileId]
  const params = { kind, partId, fileId }
  const saved = useQuery({
    queryKey: key,
    queryFn: () => FilesService.readAttachmentGallery(params),
    retry: false,
  })
  const [draft, setDraft] = useState<Draft | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [message, setMessage] = useState("")
  const [dragging, setDragging] = useState(false)
  const [expanded, setExpanded] = useState<Photo | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const selectPhotos = useRef<HTMLButtonElement>(null)
  const gallery = useRef<HTMLFieldSetElement>(null)
  const uploaded = useRef(new WeakMap<File, FilePublic>())
  const save = useMutation({
    mutationFn: async (change: Draft) => {
      const ids = []
      for (const photo of change.photos) {
        if (!(photo instanceof File)) {
          ids.push(photo.id)
          continue
        }
        let image = uploaded.current.get(photo)
        if (!image) {
          image = await FilesService.uploadFile({ formData: { file: photo } })
          uploaded.current.set(photo, image)
        }
        ids.push(image.id)
      }
      return FilesService.updateAttachmentGallery({
        ...params,
        requestBody: { previous_ids: change.previous, image_ids: ids },
      })
    },
    onSuccess: (images) => {
      client.setQueryData(key, images)
      setDraft(null)
      setMessage("")
    },
    onError: () => {
      void saved.refetch()
    },
  })
  const editable = saved.isSuccess
  const editing = Boolean(draft && editable)
  const photos = (editable ? (draft?.photos ?? saved.data) : []) ?? []
  const index = Math.min(selectedIndex, Math.max(photos.length - 1, 0))
  const selected = photos[index]
  const addingPhotos = draft?.addingPhotos
  useEffect(() => {
    if (addingPhotos) selectPhotos.current?.focus()
  }, [addingPhotos])
  const acceptFiles = useCallback(
    (files: FileList | null) => {
      if (!editing || !draft || save.isPending || !files?.length) return
      const photos = draft.photos
      const batch = Array.from(files)
      if (batch.some((f) => !isPreviewableImage(f.type))) {
        setMessage("Selecciona imágenes JPEG, PNG, GIF, WebP, AVIF o BMP.")
        return
      }
      if (photos.length + batch.length > capacity) {
        setMessage(`La galería admite hasta ${capacity} fotos.`)
        return
      }
      setMessage("")
      setDraft({ ...draft, photos: [...photos, ...batch], addingPhotos: false })
      setSelectedIndex(photos.length)
      gallery.current?.focus()
    },
    [draft, editing, save.isPending],
  )
  useEffect(() => {
    if (!editing || expanded || save.isPending) return
    function paste(event: ClipboardEvent) {
      if (!event.clipboardData?.files.length) return
      if (
        event.target instanceof Element &&
        event.target.closest(
          "input, textarea, [contenteditable=true], [role=dialog]",
        )
      )
        return
      event.preventDefault()
      acceptFiles(event.clipboardData.files)
    }
    document.addEventListener("paste", paste)
    return () => document.removeEventListener("paste", paste)
  }, [acceptFiles, editing, expanded, save.isPending])
  return (
    <div className="space-y-3">
      <AttachmentHeader
        kind={kind}
        partId={partId}
        file={file}
        context={context}
        title={galleryLabels[kind]}
      >
        {editing && draft ? (
          <>
            <Button
              size="sm"
              variant="outline"
              disabled={save.isPending}
              onClick={() => {
                setSelectedIndex(draft.initialIndex)
                setDraft(null)
                setMessage("")
                save.reset()
              }}
            >
              Cancelar
            </Button>
            <Button
              size="sm"
              disabled={save.isPending}
              onClick={() => save.mutate(draft)}
            >
              {save.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </>
        ) : (
          editable && (
            <EditGalleryButton
              onClick={() => {
                save.reset()
                setMessage("")
                setDraft({
                  initialIndex: index,
                  previous: saved.data.map((p) => p.id),
                  photos: [...saved.data],
                  addingPhotos: false,
                })
                gallery.current?.focus()
              }}
            />
          )
        )}
      </AttachmentHeader>
      {(editing || saved.isError) && sourcePicker}
      <fieldset
        ref={gallery}
        aria-label="Galería de imágenes"
        tabIndex={-1}
        className={`min-w-0 space-y-3 rounded-lg outline-none ${dragging ? "ring-2 ring-primary" : ""}`}
        onDragOver={(event) => {
          if (event.dataTransfer.types.includes("Files")) {
            event.preventDefault()
            event.dataTransfer.dropEffect =
              editing && !save.isPending ? "copy" : "none"
            setDragging(editing && !save.isPending)
          }
        }}
        onDragLeave={(event) => {
          if (
            !(event.relatedTarget instanceof Node) ||
            !event.currentTarget.contains(event.relatedTarget)
          )
            setDragging(false)
        }}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          acceptFiles(event.dataTransfer.files)
        }}
      >
        {saved.isError ? (
          <p role="alert">
            {fileErrorMessage(saved.error)}{" "}
            <Button
              size="sm"
              variant="link"
              onClick={() => void saved.refetch()}
            >
              Reintentar
            </Button>
          </p>
        ) : selected ? (
          <div className="relative overflow-hidden rounded-lg border bg-muted/20">
            <button
              type="button"
              className="flex h-[clamp(16rem,55vh,38rem)] w-full cursor-zoom-in items-center justify-center focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
              aria-label={`Ampliar ${photoName(selected)}`}
              onClick={() => setExpanded(selected)}
            >
              <GalleryImage photo={selected} />
            </button>
            {editing && draft && (
              <Button
                variant="secondary"
                size="icon"
                className="absolute right-2 top-2 size-8"
                title="Quitar foto"
                aria-label={`Quitar ${photoName(selected)}`}
                disabled={save.isPending}
                onClick={() => {
                  setMessage("")
                  setSelectedIndex(
                    Math.max(0, Math.min(index, photos.length - 2)),
                  )
                  setDraft({
                    ...draft,
                    photos: photos.filter((_, n) => n !== index),
                  })
                }}
              >
                <X />
              </Button>
            )}
          </div>
        ) : !editing ? (
          <div className="flex min-h-48 flex-col items-center justify-center gap-2 rounded-lg border bg-muted/20 text-sm text-muted-foreground sm:min-h-56">
            <ImageIcon aria-hidden="true" className="size-8" />
            {saved.isPending ? "Cargando fotos…" : "Sin fotos"}
          </div>
        ) : null}
        {photos.length > 1 && (
          <fieldset
            aria-label="Miniaturas"
            className="flex min-w-0 gap-2 overflow-x-auto py-1"
          >
            {photos.map((photo, n) => (
              <button
                key={photo instanceof File ? n : photo.id}
                type="button"
                aria-label={`Ver foto ${n + 1}: ${photoName(photo)}`}
                aria-pressed={n === index}
                onClick={() => setSelectedIndex(n)}
                className="flex h-14 w-[4.5rem] shrink-0 items-center justify-center overflow-hidden rounded-md border-2 border-transparent bg-muted/30 hover:border-muted-foreground/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring aria-pressed:border-primary sm:h-16 sm:w-20"
              >
                <GalleryImage photo={photo} />
              </button>
            ))}
          </fieldset>
        )}
        {editing &&
          draft &&
          photos.length < capacity &&
          (selected && !addingPhotos ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setDraft({ ...draft, addingPhotos: true })}
              disabled={save.isPending}
            >
              <Plus /> Añadir fotos
            </Button>
          ) : (
            <button
              ref={selectPhotos}
              type="button"
              className="flex min-h-48 w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-muted/20 p-4 hover:border-primary focus-visible:outline-ring sm:min-h-56"
              disabled={save.isPending}
              onClick={() => input.current?.click()}
            >
              <ImageIcon
                aria-hidden="true"
                className="size-8 text-muted-foreground"
              />
              <span className="text-sm font-medium">Seleccionar fotos</span>
            </button>
          ))}
        {editing && (
          <input
            ref={input}
            type="file"
            accept={IMAGE_UPLOAD_ACCEPT}
            multiple
            hidden
            onChange={(event) => {
              acceptFiles(event.target.files)
              event.target.value = ""
            }}
          />
        )}
      </fieldset>
      {(message || save.error) && (
        <p role="alert" className="text-sm text-destructive">
          {message || fileErrorMessage(save.error)}
        </p>
      )}
      <Dialog
        open={editable && expanded !== null}
        onOpenChange={(open) => {
          if (!open) setExpanded(null)
        }}
      >
        {expanded && (
          <DialogContent className="sm:max-w-5xl" aria-describedby={undefined}>
            <DialogTitle>{photoName(expanded)}</DialogTitle>
            <GalleryImage photo={expanded} expanded />
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}
