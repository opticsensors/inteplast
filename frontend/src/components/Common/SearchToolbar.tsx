import type { ReactNode } from "react"

/** Keep the search and its optional action aligned in every consultation view. */
export function SearchToolbar({
  children,
  action,
}: {
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex items-start gap-2">
      <div className="min-w-0 flex-1">{children}</div>
      {action}
    </div>
  )
}
