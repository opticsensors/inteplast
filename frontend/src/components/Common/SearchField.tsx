import { Search, X } from "lucide-react"
import type { ComponentProps } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type Props = Omit<ComponentProps<typeof Input>, "value" | "onChange"> & {
  value: string
  onValueChange: (value: string) => void
  onClear: () => void
  active?: boolean
}

/** Shared search pattern for Features, parts and drawing characteristics. */
export function SearchField({
  value,
  onValueChange,
  onClear,
  active,
  ...props
}: Props) {
  return (
    <div className="relative">
      <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        {...props}
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        className="pr-10 pl-9"
      />
      {(active ?? Boolean(value)) && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute top-1/2 right-1 size-7 -translate-y-1/2"
          onClick={onClear}
        >
          <X className="size-4" />
          <span className="sr-only">Limpiar busqueda</span>
        </Button>
      )}
    </div>
  )
}
