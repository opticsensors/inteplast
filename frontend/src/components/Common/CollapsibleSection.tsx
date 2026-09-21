import { ChevronDown } from "lucide-react"
import { type ReactNode, useState } from "react"

import { cn } from "@/lib/utils"

interface CollapsibleSectionProps {
  title: ReactNode
  /** Contenido editable junto al boton de desplegar, nunca dentro de el. */
  headerContent?: ReactNode
  leading?: ReactNode
  icon?: ReactNode
  /** Acciones a la derecha del titulo (p. ej. el boton de anadir). */
  actions?: ReactNode
  defaultOpen?: boolean
  keepMounted?: boolean
  storageKey?: string
  children: ReactNode
  className?: string
  titleClassName?: string
}

/** Panel desplegable. Hecho a mano para no anadir otra dependencia de Radix. */
export function CollapsibleSection({
  title,
  headerContent,
  leading,
  icon,
  actions,
  defaultOpen = true,
  keepMounted = false,
  storageKey,
  children,
  className,
  titleClassName,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(() => {
    try {
      const saved = storageKey ? sessionStorage.getItem(storageKey) : null
      return saved === null ? defaultOpen : saved === "true"
    } catch {
      return defaultOpen
    }
  })

  return (
    <div className={cn("rounded-lg border", className)}>
      <div className="flex items-center gap-2 px-3 py-2">
        {leading}
        <button
          type="button"
          onClick={() =>
            setIsOpen((open) => {
              try {
                if (storageKey)
                  sessionStorage.setItem(storageKey, String(!open))
              } catch {
                /* Storage may be disabled. */
              }
              return !open
            })
          }
          aria-expanded={isOpen}
          className={cn(
            "flex items-center gap-2 text-left text-sm font-medium",
            headerContent ? "shrink-0" : "flex-1",
            titleClassName,
          )}
        >
          <ChevronDown
            className={cn(
              "size-4 shrink-0 text-muted-foreground transition-transform",
              !isOpen && "-rotate-90",
            )}
          />
          {icon}
          {headerContent ? <span className="sr-only">{title}</span> : title}
        </button>
        {headerContent}
        {actions}
      </div>
      {(isOpen || keepMounted) && (
        <div hidden={!isOpen} className="space-y-2 px-3 pb-3">
          {children}
        </div>
      )}
    </div>
  )
}
