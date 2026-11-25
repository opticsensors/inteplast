import { ImagePlus, Maximize2, Pencil } from "lucide-react"
import type { ComponentProps } from "react"

import type { FilePublic } from "@/client"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { FeatureThumbnail } from "./FeatureCard"

/** Square shared by piece and feature headers, including their empty covers. */
export const COVER_SIZE = "size-48 sm:size-[300px]"

export function RetryCoverButton({ onRetry }: { onRetry: () => void }) {
  return (
    <Button type="button" size="sm" variant="outline" onClick={onRetry}>
      Reintentar portada
    </Button>
  )
}

/** One click target, including the corner icon; never nest a second button. */
export function CoverButton({
  image,
  name,
  editable = false,
  hasCover = Boolean(image),
  checking,
  className,
  ...props
}: ComponentProps<"button"> & {
  image?: FilePublic | null
  name: string
  editable?: boolean
  hasCover?: boolean
  checking?: boolean
}) {
  const label = editable
    ? hasCover
      ? "Editar portada"
      : "Añadir portada"
    : "Ampliar portada"
  const Icon = editable ? (hasCover ? Pencil : ImagePlus) : Maximize2
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "group relative shrink-0 cursor-pointer rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        COVER_SIZE,
        className,
      )}
      {...props}
    >
      <FeatureThumbnail
        feature={{ image, name }}
        checking={checking}
        fit="contain"
        className="size-full"
      />
      {editable && !hasCover && (
        <span className="absolute inset-x-1 bottom-3 text-xs font-medium">
          Añadir portada
        </span>
      )}
      {(hasCover || !editable) && (
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
