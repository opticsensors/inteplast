import { ImagePlus, X } from "lucide-react"
import { useRef, useState } from "react"
import { type FilePublic, FilesService } from "@/client"
import { RichTextEditor, RichTextView } from "@/components/Common/RichText"
import { Button } from "@/components/ui/button"
import { fileErrorMessage, useFileAccess } from "@/hooks/useFileAccess"
import { SaveStatus } from "./SaveStatus"
import { usePendingTask } from "./usePendingTask"
import { IMAGE_UPLOAD_ACCEPT, isPreviewableImage } from "./viewers"

// Keep image references in the note's existing Markdown body, never temporary access URLs.
const IMAGE_LINE = /^!\[([^\]\n]*)\]\(file:([\w-]+)\)\s*$/
const splitBody = (body: string) => {
  const images: { id: string; name: string; source: string }[] = []
  const text = body
    .split("\n")
    .filter((line) => {
      const match = line.match(IMAGE_LINE)
      if (!match) return true
      if (!images.some((image) => image.id === match[2]))
        images.push({ id: match[2], name: match[1], source: line })
      return false
    })
    .join("\n")
    .trimEnd()
  return { text, images }
}

function NoteImage({ id, name }: { id: string; name: string }) {
  const { url, isError } = useFileAccess(id)
  const [failed, setFailed] = useState(false)
  return isError || failed ? (
    <p role="alert" className="text-sm text-destructive">
      No se ha podido cargar {name || "la imagen"}.
    </p>
  ) : url ? (
    <img
      src={url}
      alt={name || "Imagen de la nota"}
      className="max-h-80 max-w-full rounded-md border object-contain"
      onError={() => setFailed(true)}
    />
  ) : (
    <p className="text-xs text-muted-foreground">Cargando imagen…</p>
  )
}

export function NoteBodyView({ value }: { value?: string | null }) {
  const { text, images } = splitBody(value ?? "")
  return (
    <div className="space-y-3 break-words">
      <RichTextView value={text} />
      {images.map((image) => (
        <NoteImage key={image.id} {...image} />
      ))}
    </div>
  )
}

export function NoteBodyEditor({
  value,
  onChange,
  flush,
}: {
  value: string
  onChange: (value: string) => void
  flush: () => Promise<boolean>
}) {
  const current = useRef(value)
  current.current = value
  const input = useRef<HTMLInputElement>(null)
  const uploaded = useRef<{ file: File; saved: FilePublic } | null>(null)
  const [message, setMessage] = useState("")
  const { text, images } = splitBody(value)
  const upload = usePendingTask(async (file: File) => {
    try {
      if (!isPreviewableImage(file.type))
        throw new Error("Usa una imagen JPEG, PNG, GIF, WebP, AVIF o BMP.")
      const saved =
        uploaded.current?.file === file
          ? uploaded.current.saved
          : await FilesService.uploadFile({ formData: { file } })
      uploaded.current = { file, saved }
      const name = saved.filename.replace(/[[\]\r\n]/g, " ")
      if (
        !splitBody(current.current).images.some(
          (image) => image.id === saved.id,
        )
      )
        onChange(`${current.current.trimEnd()}\n\n![${name}](file:${saved.id})`)
      if (!(await flush()))
        throw new Error("No se ha podido guardar la imagen en la nota.")
      setMessage("")
    } catch (error) {
      setMessage(fileErrorMessage(error))
      throw error
    }
  })
  return (
    <div className="space-y-3">
      <RichTextEditor
        value={text}
        onChange={(text) =>
          onChange([text, ...images.map((image) => image.source)].join("\n\n"))
        }
        placeholder="Detalles: **negrita**, *cursiva*, `codigo` y listas con guion"
      />
      {images.map((image) => (
        <div key={image.id} className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <NoteImage {...image} />
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0 text-destructive"
            aria-label={`Quitar imagen ${image.name}`}
            onClick={() =>
              onChange(
                [
                  text,
                  ...images
                    .filter((item) => item.id !== image.id)
                    .map((item) => item.source),
                ].join("\n\n"),
              )
            }
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}
      <input
        ref={input}
        type="file"
        accept={IMAGE_UPLOAD_ACCEPT}
        className="hidden"
        aria-label="Imagen de la nota"
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ""
          if (!file) return
          if (!isPreviewableImage(file.type)) {
            setMessage("Usa una imagen JPEG, PNG, GIF, WebP, AVIF o BMP.")
            return
          }
          setMessage("")
          void upload.run(file)
        }}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={upload.pending}
        onClick={() => input.current?.click()}
      >
        <ImagePlus className="size-4" />
        Añadir imagen
      </Button>
      {message && (
        <p role="alert" className="text-xs text-destructive">
          {message}
        </p>
      )}
      <SaveStatus
        saving={upload.pending}
        error={upload.error}
        retry={upload.retry}
      />
    </div>
  )
}
