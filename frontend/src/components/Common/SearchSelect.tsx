import { Check, ChevronDown } from "lucide-react"
import { useEffect, useId, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { SearchField } from "./SearchField"

export type SearchOption = { value: string; label: string }

/** The shared filter style, with text search and keyboard selection inside. */
export function SearchSelect({
  label,
  value,
  options,
  placeholder,
  emptyLabel,
  onChange,
  disabled = false,
  selectedLabel,
  compact = false,
  defaultOpen = false,
  showLabel = false,
}: {
  label: string
  value?: string | null
  options: SearchOption[]
  placeholder: string
  emptyLabel: string
  onChange: (value: string | undefined) => void
  disabled?: boolean
  selectedLabel?: string
  compact?: boolean
  defaultOpen?: boolean
  showLabel?: boolean
}) {
  const id = useId()
  const root = useRef<HTMLFieldSetElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(defaultOpen)
  const [query, setQuery] = useState("")
  const [active, setActive] = useState(0)
  const normalize = (text: string) =>
    text
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase()
  const choices = [{ value: "", label: emptyLabel }, ...options].filter(
    (item) => normalize(item.label).includes(normalize(query.trim())),
  )
  const current = Math.min(active, Math.max(0, choices.length - 1))
  const selected = options.find((item) => item.value === value)
  useEffect(() => {
    if (!open) return
    input.current?.focus()
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener("pointerdown", close)
    return () => document.removeEventListener("pointerdown", close)
  }, [open])
  useEffect(() => {
    if (open)
      document
        .getElementById(`${id}-option-${current}`)
        ?.scrollIntoView({ block: "nearest" })
  }, [open, current, id])
  const choose = (next: string) => {
    if (next !== (value ?? "")) onChange(next || undefined)
    setOpen(false)
    trigger.current?.focus()
  }
  return (
    <fieldset
      ref={root}
      className="relative min-w-0"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false)
      }}
    >
      {showLabel && (
        <legend className="mb-1.5 text-sm font-medium">{label}</legend>
      )}
      <Button
        ref={trigger}
        type="button"
        variant="outline"
        role="combobox"
        aria-label={label}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={`${id}-dialog`}
        disabled={disabled}
        className={cn(
          "h-9 w-full justify-between gap-2 px-3 font-normal",
          compact && "h-7 px-2",
        )}
        onClick={() => {
          setQuery("")
          setActive(0)
          setOpen(!open)
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault()
            setQuery("")
            setActive(0)
            setOpen(true)
          }
        }}
      >
        <span className="truncate">
          {selected?.label ??
            (value
              ? (selectedLabel ?? "Selección no disponible")
              : placeholder)}
        </span>
        <ChevronDown className="size-4 shrink-0 opacity-50" />
      </Button>
      {open && (
        <div
          id={`${id}-dialog`}
          role="dialog"
          aria-label={`Selector de ${label.toLocaleLowerCase()}`}
          className="absolute top-full right-0 left-0 z-40 mt-1 rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
        >
          <div className="p-1">
            <SearchField
              ref={input}
              value={query}
              onValueChange={(q) => {
                setQuery(q)
                setActive(0)
              }}
              onClear={() => {
                setQuery("")
                setActive(0)
                input.current?.focus()
              }}
              placeholder={`Buscar ${label.toLocaleLowerCase()}…`}
              aria-label={`Buscar ${label.toLocaleLowerCase()}`}
              role="combobox"
              aria-expanded={true}
              aria-controls={`${id}-options`}
              aria-autocomplete="list"
              aria-activedescendant={
                choices.length ? `${id}-option-${current}` : undefined
              }
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  event.preventDefault()
                  setOpen(false)
                  trigger.current?.focus()
                }
                if (event.key === "Tab") setOpen(false)
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault()
                  setActive(
                    Math.max(
                      0,
                      Math.min(
                        choices.length - 1,
                        current + (event.key === "ArrowDown" ? 1 : -1),
                      ),
                    ),
                  )
                }
                if (event.key === "Enter") {
                  event.preventDefault()
                  if (choices[current]) choose(choices[current].value)
                }
              }}
            />
          </div>
          <div
            id={`${id}-options`}
            role="listbox"
            aria-label={label}
            className="max-h-60 overflow-y-auto"
          >
            {choices.map((item, index) => (
              <button
                key={item.value}
                id={`${id}-option-${index}`}
                type="button"
                role="option"
                tabIndex={-1}
                aria-selected={item.value === (value ?? "")}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(item.value)}
                className={cn(
                  "flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent",
                  index === current && "bg-accent",
                )}
              >
                <span className="min-w-0 break-words">{item.label}</span>
                {item.value === (value ?? "") && (
                  <Check className="size-4 shrink-0" />
                )}
              </button>
            ))}
            {!choices.length && (
              <p className="p-3 text-sm text-muted-foreground">
                Sin coincidencias.
              </p>
            )}
          </div>
        </div>
      )}
    </fieldset>
  )
}
