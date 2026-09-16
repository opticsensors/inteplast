import { useMutation } from "@tanstack/react-query"
import { ImageIcon, Loader2, Paperclip, Upload, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { type FilePublic, FilesService } from "@/client"
import { SaveStatus } from "@/components/Features/SaveStatus"
import { usePendingTask } from "@/components/Features/usePendingTask"
import {
  IMAGE_UPLOAD_ACCEPT,
  isPreviewableImage,
} from "@/components/Features/viewers"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { useFileAccess } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import { formatFileSize, handleError } from "@/utils"

interface FileUploadProps {
  value: FilePublic | null
  onChange: (file: FilePublic | null) => void
  /** "image" pinta el cuadro con vista previa; "file" una fila con el nombre. */
  variant?: "image" | "file"
  accept?: string
  className?: string
  /** Tamaño del cuadro de imagen. La ficha lo iguala al de su foto. */
  boxClassName?: string
  /** Fixed rows shared with the CAD tab in the cover dialog. */
  coverLayout?: boolean
  /** Restrict clipboard images to this editor's dialog. */
  pasteInDialog?: boolean
  onUploadStateChange?: (state: { pending: boolean; error: boolean }) => void
}

/**
 * Sube un fichero al backend y devuelve su ficha. Acepta clic o drag and drop.
 * Solo guarda la referencia: quien lo use decide donde se asocia el `id`.
 */
export function FileUpload({
  value,
  onChange,
  variant = "file",
  accept,
  className,
  boxClassName,
  coverLayout = false,
  pasteInDialog = false,
  onUploadStateChange,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  const { showErrorToast } = useCustomToast()
  const { url } = useFileAccess(value?.id)

  const mutation = useMutation({
    mutationFn: (file: File) => FilesService.uploadFile({ formData: { file } }),
    onSuccess: (uploaded) => onChange(uploaded),
    onError: handleError.bind(showErrorToast),
  })
  const upload = usePendingTask((file: File) => mutation.mutateAsync(file))
  useEffect(() => {
    onUploadStateChange?.({ pending: upload.pending, error: upload.error })
  }, [upload.pending, upload.error, onUploadStateChange])

  const handleFiles = (files: FileList | null) => {
    if (upload.pending) return
    const file = files?.[0]
    if (!file) return
    if (variant === "image" && !isPreviewableImage(file.type)) {
      showErrorToast("Usa una imagen JPEG, PNG, GIF, WebP, AVIF o BMP.")
      return
    }
    void upload.run(file)
  }

  const paste = useRef(handleFiles)
  paste.current = handleFiles
  useEffect(() => {
    if (variant !== "image") return
    const onPaste = (event: ClipboardEvent) => {
      const target = event.target instanceof Element ? event.target : null
      if (target?.closest("input, textarea, [contenteditable=true]")) return
      const dialog = target?.closest('[role="dialog"]')
      if (pasteInDialog) {
        if (!dialog || dialog !== rootRef.current?.closest('[role="dialog"]'))
          return
      } else if (dialog) return
      const files = event.clipboardData?.files
      if (!files?.length) return
      event.preventDefault()
      paste.current(files)
    }
    window.addEventListener("paste", onPaste)
    return () => window.removeEventListener("paste", onPaste)
  }, [variant, pasteInDialog])

  const dropHandlers = {
    onDragOver: (event: React.DragEvent) => {
      event.preventDefault()
      setIsDragging(true)
    },
    onDragLeave: () => setIsDragging(false),
    onDrop: (event: React.DragEvent) => {
      event.preventDefault()
      setIsDragging(false)
      handleFiles(event.dataTransfer.files)
    },
  }

  const input = (
    <input
      ref={inputRef}
      type="file"
      accept={variant === "image" ? IMAGE_UPLOAD_ACCEPT : accept}
      className="hidden"
      onChange={(event) => {
        handleFiles(event.target.files)
        event.target.value = ""
      }}
    />
  )

  if (variant === "image") {
    return (
      <div
        ref={rootRef}
        className={cn(
          "relative",
          coverLayout &&
            "row-span-2 grid grid-rows-[2.25rem_var(--cover-size)] gap-3",
          className,
        )}
      >
        <button
          type="button"
          aria-label="Seleccionar imagen"
          data-slot={coverLayout ? "cover-surface" : undefined}
          title="Seleccionar imagen del ordenador"
          disabled={upload.pending}
          onClick={() => inputRef.current?.click()}
          {...dropHandlers}
          className={cn(
            "flex size-28 items-center justify-center overflow-hidden rounded-md border-2 border-dashed transition-colors",
            isDragging ? "border-primary bg-accent" : "border-input",
            "hover:border-primary hover:bg-accent/50",
            coverLayout && "row-start-2",
            boxClassName,
          )}
        >
          {mutation.isPending ? (
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          ) : value && url && isPreviewableImage(value.content_type) ? (
            <img
              src={url}
              alt={value.filename}
              className="size-full object-contain"
            />
          ) : (
            <ImageIcon className="size-8 text-muted-foreground" />
          )}
        </button>
        {value && !mutation.isPending && (
          <Button
            type="button"
            variant="secondary"
            size="icon"
            className={cn(
              "absolute size-6 rounded-full",
              coverLayout
                ? "right-2 top-[calc(3rem+0.5rem)]"
                : "-top-2 -right-2",
            )}
            onClick={() => onChange(null)}
          >
            <X className="size-3" />
            <span className="sr-only">Quitar imagen</span>
          </Button>
        )}
        {input}
        <p
          className={cn(
            "text-center text-xs text-muted-foreground",
            coverLayout
              ? "row-start-1 flex items-center justify-center"
              : "mt-1",
          )}
        >
          Arrastra, pega (Ctrl+V) o haz clic para elegir
        </p>
        <div
          className={
            coverLayout
              ? "absolute inset-x-2 bottom-2 bg-background/95 empty:hidden"
              : undefined
          }
        >
          <SaveStatus
            error={upload.error}
            saving={upload.pending}
            retry={upload.retry}
          />
        </div>
      </div>
    )
  }

  if (value) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
          className,
        )}
      >
        <Paperclip className="size-4 shrink-0 text-muted-foreground" />
        <span className="truncate">{value.filename}</span>
        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
          {formatFileSize(value.size)}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-6 shrink-0"
          onClick={() => onChange(null)}
        >
          <X className="size-3" />
          <span className="sr-only">Quitar fichero</span>
        </Button>
      </div>
    )
  }

  return (
    <>
      <button
        type="button"
        disabled={upload.pending}
        onClick={() => inputRef.current?.click()}
        {...dropHandlers}
        className={cn(
          "flex w-full flex-col items-center gap-1 rounded-md border-2 border-dashed px-3 py-6 text-sm text-muted-foreground transition-colors",
          isDragging ? "border-primary bg-accent" : "border-input",
          "hover:border-primary hover:bg-accent/50",
          className,
        )}
      >
        {mutation.isPending ? (
          <Loader2 className="size-5 animate-spin" />
        ) : (
          <Upload className="size-5" />
        )}
        <span>Arrastra un fichero o haz clic para seleccionarlo</span>
      </button>
      {input}
      <SaveStatus
        error={upload.error}
        saving={upload.pending}
        retry={upload.retry}
      />
    </>
  )
}
