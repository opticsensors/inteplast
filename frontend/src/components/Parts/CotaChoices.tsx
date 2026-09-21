import { useState } from "react"
import { Button } from "@/components/ui/button"
import type { Entry } from "./types"

export function CotaChoices({
  entries,
  selected,
  onSelect,
}: {
  entries: Entry[]
  selected?: string
  onSelect: (code: string) => void
}) {
  const [limit, setLimit] = useState(24)
  return (
    <fieldset className="flex flex-wrap gap-2">
      <legend className="sr-only">Cotas disponibles</legend>
      {entries.slice(0, limit).map((entry) => (
        <Button
          key={entry.id}
          type="button"
          size="sm"
          variant={selected === entry.id ? "secondary" : "outline"}
          aria-pressed={selected === entry.id}
          onClick={() => onSelect(entry.id)}
          title={entry.title || undefined}
        >
          {entry.id}
        </Button>
      ))}
      {entries.length > limit && (
        <Button
          type="button"
          variant="link"
          size="sm"
          className="font-normal text-muted-foreground underline underline-offset-4"
          onClick={() => setLimit(limit + 24)}
        >
          Mostrar más cotas
        </Button>
      )}
    </fieldset>
  )
}
