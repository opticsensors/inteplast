import { useMutation } from "@tanstack/react-query"
import { ImageIcon, Loader2, Paperclip, Upload, X } from "lucide-react"
import { useRef, useState } from "react"

import { type FilePublic, FilesService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { fileUrl, formatFileSize, handleError } from "@/utils"

interface FileUploadProps {
  value: FilePublic | null
  onChange: (file: FilePublic | null) => void
  /** "image" pinta el cuadro con vista previa; "file" una fila con el nombre. */
  variant?: "image" | "file"
  accept?: string
  className?: string
  /** Tamaño del cuadro de imagen. La ficha lo iguala al de su foto. */
  boxClassName?: string
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
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const { showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (file: File) => FilesService.uploadFile({ formData: { file } }),
    onSuccess: (uploaded) => onChange(uploaded),
    onError: handleError.bind(showErrorToast),
  })

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0]
    if (file) mutation.mutate(file)
  }

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
      accept={accept}
      className="hidden"
      onChange={(event) => {
        handleFiles(event.target.files)
        event.target.value = ""
      }}
    />
  )

  if (variant === "image") {
    return (
      <div className={cn("relative", className)}>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          {...dropHandlers}
          className={cn(
            "flex size-28 items-center justify-center overflow-hidden rounded-md border-2 border-dashed transition-colors",
            isDragging ? "border-primary bg-accent" : "border-input",
            "hover:border-primary hover:bg-accent/50",
            boxClassName,
          )}
        >
          {mutation.isPending ? (
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          ) : value ? (
            <img
              src={fileUrl(value.id)}
              alt={value.filename}
              className="size-full object-cover"
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
            className="absolute -top-2 -right-2 size-6 rounded-full"
            onClick={() => onChange(null)}
          >
            <X className="size-3" />
            <span className="sr-only">Quitar imagen</span>
          </Button>
        )}
        {input}
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
    </>
  )
}
