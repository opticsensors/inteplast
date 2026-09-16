import { ImagePlus, Maximize2, Pencil } from "lucide-react"
import type { ComponentProps } from "react"

import type { FilePublic } from "@/client"
import { cn } from "@/lib/utils"
import { FeatureThumbnail } from "./FeatureCard"

/** One click target, including the corner icon; never nest a second button. */
export function CoverButton({
  image,
  name,
  editable = false,
  className,
  ...props
}: ComponentProps<"button"> & {
  image?: FilePublic | null
  name: string
  editable?: boolean
}) {
  const label = editable
    ? image
      ? "Editar portada"
      : "Añadir portada"
    : "Ampliar portada"
  const Icon = editable ? (image ? Pencil : ImagePlus) : Maximize2
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "group relative size-32 shrink-0 cursor-pointer rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:size-48",
        className,
      )}
      {...props}
    >
      <FeatureThumbnail
        feature={{ image, name }}
        fit="contain"
        className="size-full"
      />
      {editable && !image && (
        <span className="absolute inset-x-1 bottom-3 text-xs font-medium">
          Añadir portada
        </span>
      )}
      {(image || !editable) && (
        <span
          aria-hidden="true"
          className="absolute bottom-2 right-2 flex size-8 items-center justify-center rounded-md border bg-background/95 text-foreground opacity-0 shadow-sm transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
        >
          <Icon className="size-3.5" />
        </span>
      )}
    </button>
  )
}
