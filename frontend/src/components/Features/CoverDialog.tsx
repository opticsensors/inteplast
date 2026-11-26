import type { ComponentProps } from "react"

import { DialogContent } from "@/components/ui/dialog"

// Each editor tab gives the viewport all space between its toolbar and footer.
export const COVER_EDITOR_ROWS =
  "grid h-full min-h-0 grid-rows-[2.25rem_minmax(0,1fr)_auto] gap-3 data-[state=inactive]:hidden"

export function CoverDialog({
  ...props
}: ComponentProps<typeof DialogContent>) {
  return (
    <DialogContent
      {...props}
      scrollable
      className="h-[90dvh] min-h-0 w-[92vw] max-w-full grid-rows-[auto_minmax(0,1fr)] gap-3 overflow-hidden p-4 sm:max-w-[1400px]"
    />
  )
}
