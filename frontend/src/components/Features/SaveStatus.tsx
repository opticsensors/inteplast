import { Button } from "@/components/ui/button"

export function SaveStatus({
  error,
  saving,
  retry,
}: {
  error: boolean
  saving: boolean
  retry: () => Promise<boolean>
}) {
  if (error)
    return (
      <div
        role="alert"
        className="flex items-center gap-2 px-2 py-1 text-xs text-destructive"
      >
        <span>Cambios sin guardar. Corrige los campos o reintenta.</span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            void retry()
          }}
        >
          Reintentar
        </Button>
      </div>
    )
  return saving ? (
    <output className="px-2 text-xs text-muted-foreground">Guardando...</output>
  ) : null
}
