import { Check, ChevronDown, Loader2, Plus } from "lucide-react"
import { useEffect, useId, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { SearchField } from "./SearchField"

export type SearchOption = { value: string; label: string }

/**
 * The shared filter style, with text search and keyboard selection inside.
 *
 * With `onCreate`, the last row is «+ Añadir …» (`createLabel`), styled like «Añadir
 * pieza» and «Añadir feature». It opens an empty field, as «Añadir cota» does, filled with
 * the text already searched; Enter or leaving the field saves it, Escape cancels.
 * `onCreate` returns the value to select (an existing one when the name already exists).
 */
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
  onCreate,
  createLabel = "Añadir",
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
  onCreate?: (text: string) => Promise<string>
  createLabel?: string
}) {
  const id = useId()
  const root = useRef<HTMLFieldSetElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(defaultOpen)
  const [query, setQuery] = useState("")
  const [active, setActive] = useState(0)
  const [adding, setAdding] = useState(false)
  const cancelled = useRef(false)
  const [draft, setDraft] = useState("")
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState("")
  const normalize = (text: string) =>
    text
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .join(" ")
  const typed = query.trim().replace(/\s+/g, " ")
  const choices = [{ value: "", label: emptyLabel }, ...options].filter(
    (item) => normalize(item.label).includes(normalize(typed)),
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
  const save = () => {
    const name = draft.trim().replace(/\s+/g, " ")
    if (!onCreate || creating) return
    if (!name) {
      setAdding(false)
      return
    }
    setCreating(true)
    setCreateError("")
    onCreate(name)
      .then((created) => {
        onChange(created)
        setAdding(false)
        setOpen(false)
        trigger.current?.focus()
      })
      .catch(() => setCreateError("No se ha podido añadir. Reinténtalo."))
      .finally(() => setCreating(false))
  }
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
          setAdding(false)
          setCreateError("")
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
          {onCreate && (
            <div className="mt-1 border-t p-1 pt-2">
              {adding ? (
                <div className="flex items-center gap-2">
                  <Input
                    autoFocus
                    aria-label={createLabel}
                    placeholder="Nombre"
                    value={draft}
                    disabled={creating}
                    onChange={(event) => setDraft(event.target.value)}
                    onBlur={() => {
                      // Leaving the field saves, unless Escape has just cancelled it.
                      if (cancelled.current) cancelled.current = false
                      else save()
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault()
                        save()
                      }
                      if (event.key === "Escape") {
                        event.preventDefault()
                        event.stopPropagation()
                        cancelled.current = true
                        setAdding(false)
                        setCreateError("")
                        input.current?.focus()
                      }
                    }}
                    className="h-8"
                  />
                  {creating && (
                    <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />
                  )}
                </div>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setDraft(typed)
                    setCreateError("")
                    setAdding(true)
                  }}
                >
                  <Plus className="mr-1 size-3.5" />
                  {createLabel}
                </Button>
              )}
              {createError && (
                <p
                  role="alert"
                  className="px-1 pt-1.5 text-sm text-destructive"
                >
                  {createError}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </fieldset>
  )
}
