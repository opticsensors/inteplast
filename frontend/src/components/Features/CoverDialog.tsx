import type { ComponentProps, CSSProperties } from "react"

import { DialogContent } from "@/components/ui/dialog"

// Both editor tabs share the same toolbar, square and action rows.
export const COVER_EDITOR_ROWS =
  "grid grid-rows-[2.25rem_var(--cover-size)_auto] gap-3"

export function CoverDialog({
  ...props
}: ComponentProps<typeof DialogContent>) {
  return (
    <DialogContent
      {...props}
      scrollable
      className="w-[calc(var(--cover-size)+2rem+2px)] max-w-none gap-3 p-4 sm:max-w-none"
      style={
        {
          "--cover-size": "min(720px, 75dvh, calc(100vw - 4rem - 2px))",
        } as CSSProperties
      }
    />
  )
}
