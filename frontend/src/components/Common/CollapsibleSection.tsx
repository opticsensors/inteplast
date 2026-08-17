import { ChevronDown } from "lucide-react"
import { type ReactNode, useState } from "react"

import { cn } from "@/lib/utils"

interface CollapsibleSectionProps {
  title: ReactNode
  icon?: ReactNode
  /** Acciones a la derecha del titulo (p. ej. el boton de anadir). */
  actions?: ReactNode
  defaultOpen?: boolean
  children: ReactNode
  className?: string
}

/** Panel desplegable. Hecho a mano para no anadir otra dependencia de Radix. */
export function CollapsibleSection({
  title,
  icon,
  actions,
  defaultOpen = true,
  children,
  className,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className={cn("rounded-lg border", className)}>
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={() => setIsOpen((open) => !open)}
          className="flex flex-1 items-center gap-2 text-left text-sm font-medium"
        >
          <ChevronDown
            className={cn(
              "size-4 shrink-0 text-muted-foreground transition-transform",
              !isOpen && "-rotate-90",
            )}
          />
          {icon}
          {title}
        </button>
        {actions}
      </div>
      {isOpen && <div className="space-y-2 px-3 pb-3">{children}</div>}
    </div>
  )
}
