import { ChevronDown } from "lucide-react"
import { type ReactNode, useId, useState } from "react"

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
  variant?: "panel" | "row" | "plain"
  compact?: boolean
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
  variant = "panel",
  compact = false,
}: CollapsibleSectionProps) {
  const contentId = useId()
  const [isOpen, setIsOpen] = useState(() => {
    try {
      const saved = storageKey ? sessionStorage.getItem(storageKey) : null
      return saved === null ? defaultOpen : saved === "true"
    } catch {
      return defaultOpen
    }
  })

  return (
    <div
      className={cn(
        variant === "panel" && "rounded-lg border",
        variant === "row" && "border-b",
        className,
      )}
    >
      <div
        className={cn(
          "flex items-center gap-2",
          variant === "row" ? "py-3" : "px-3 py-2",
          variant === "plain" && "rounded-md bg-muted/50",
          compact && "py-1.5",
        )}
      >
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
          aria-controls={contentId}
          className={cn(
            "flex min-w-0 items-center gap-3 rounded-sm text-left text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            headerContent ? "shrink-0" : "flex-1",
            variant === "row" && "font-normal",
            compact && "gap-2",
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
        <div
          id={contentId}
          hidden={!isOpen}
          className={cn(
            "space-y-2",
            variant === "plain" ? "pt-4" : "px-3 pb-3",
            variant === "row" && "pl-7",
            compact && "pb-2",
          )}
        >
          {children}
        </div>
      )}
    </div>
  )
}
