import { FileSearch } from "lucide-react"
import { Button } from "@/components/ui/button"

export function DrawingToggle({
  active = false,
  disabled = false,
  onClick,
}: {
  active?: boolean
  disabled?: boolean
  onClick?: () => void
}) {
  return (
    <Button
      type="button"
      variant={active ? "secondary" : "outline"}
      className="h-9 shrink-0 border"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
    >
      <FileSearch className="size-4" />
      Plano
    </Button>
  )
}
