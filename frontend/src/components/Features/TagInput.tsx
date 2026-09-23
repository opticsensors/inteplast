import { X } from "lucide-react"
import { type ComponentProps, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function TagInput({
  value,
  onChange,
  onBlur,
  ...props
}: Omit<ComponentProps<typeof Input>, "value" | "onChange"> & {
  value: string
  onChange: (value: string) => void
}) {
  const [draft, setDraft] = useState("")
  const tags = value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean)
  const commit = () => {
    const added = draft
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
    if (added.length) onChange([...new Set([...tags, ...added])].join(", "))
    setDraft("")
  }
  return (
    <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-input px-2 py-1 shadow-xs focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50">
      {tags.map((tag) => (
        <Button
          key={tag}
          type="button"
          variant="secondary"
          size="sm"
          className="h-6 max-w-full gap-1 px-2 font-normal"
          aria-label={`Quitar tag ${tag}`}
          onClick={() =>
            onChange(tags.filter((item) => item !== tag).join(", "))
          }
        >
          <span className="truncate">{tag}</span>
          <X className="size-3 shrink-0" />
        </Button>
      ))}
      <Input
        {...props}
        value={draft}
        placeholder="Añadir tag…"
        className="h-6 min-w-24 flex-1 rounded-none border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
        onChange={(event) => setDraft(event.target.value)}
        onBlur={(event) => {
          commit()
          onBlur?.(event)
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === ",") {
            event.preventDefault()
            commit()
          }
        }}
      />
    </div>
  )
}
