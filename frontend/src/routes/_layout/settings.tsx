import { useMutation, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { RotateCcw } from "lucide-react"
import { useId } from "react"
import {
  type CadPreferences,
  type CurrentUserPublic,
  UsersService,
} from "@/client"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { defaultCadPreferences } from "@/hooks/useCadPreferences"

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
  head: () => ({ meta: [{ title: "Ajustes de usuario - INTEPLAST" }] }),
})

function Choice<T extends string>({
  label,
  value,
  options,
  change,
}: {
  label: string
  value: T
  options: readonly (readonly [T, string])[]
  change: (value: T) => void
}) {
  const name = useId()
  return (
    <div
      role="radiogroup"
      aria-labelledby={name}
      className="grid gap-2 py-4 sm:grid-cols-[1fr_auto] sm:items-center"
    >
      <span id={name} className="text-sm font-medium">
        {label}
      </span>
      <div className="inline-flex w-fit rounded-lg bg-muted p-1">
        {options.map(([option, title]) => (
          <label key={option} className="relative cursor-pointer">
            <input
              className="peer sr-only"
              type="radio"
              name={name}
              value={option}
              checked={value === option}
              onChange={() => change(option)}
            />
            <span className="block rounded-md px-3 py-1.5 text-sm text-muted-foreground peer-checked:bg-background peer-checked:text-foreground peer-checked:shadow-sm peer-focus-visible:ring-2 peer-focus-visible:ring-ring">
              {title}
            </span>
          </label>
        ))}
      </div>
    </div>
  )
}

function UserSettings() {
  const { user } = useAuth()
  const cache = useQueryClient()
  const save = useMutation({
    mutationFn: (requestBody: CadPreferences) =>
      UsersService.updateCadPreferences({ requestBody }),
    onMutate: async (patch) => {
      await cache.cancelQueries({ queryKey: ["currentUser"], exact: true })
      cache.setQueryData<CurrentUserPublic>(
        ["currentUser"],
        (current) => current && { ...current, ...patch },
      )
      return user
    },
    onError: (_error, _patch, previous) => {
      if (previous) cache.setQueryData(["currentUser"], previous)
    },
    onSuccess: (updated) => cache.setQueryData(["currentUser"], updated),
  })
  if (!user) return null
  const {
    cad_projection = "orthographic",
    cad_controls = "solidworks",
    invert_zoom = false,
  } = user
  const isDefault =
    cad_projection === defaultCadPreferences.cad_projection &&
    cad_controls === defaultCadPreferences.cad_controls &&
    invert_zoom === defaultCadPreferences.invert_zoom
  return (
    <section className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Ajustes de usuario</h1>
      <div className="rounded-lg border bg-card px-5 py-4">
        <h2 className="text-lg font-semibold">Visor CAD</h2>
        <fieldset
          aria-label="Preferencias del visor CAD"
          disabled={save.isPending}
          className="divide-y"
        >
          <Choice
            label="Proyección"
            value={cad_projection}
            options={[
              ["orthographic", "Ortográfica"],
              ["perspective", "Perspectiva 45°"],
            ]}
            change={(cad_projection) => save.mutate({ cad_projection })}
          />
          <Choice
            label="Controles"
            value={cad_controls}
            options={[
              ["solidworks", "Tipo SolidWorks"],
              ["classic", "Clásicos"],
            ]}
            change={(cad_controls) => save.mutate({ cad_controls })}
          />
          <Choice
            label="Acercar con la rueda"
            value={invert_zoom ? "back" : "forward"}
            options={[
              ["forward", "Hacia la pantalla"],
              ["back", "Hacia ti"],
            ]}
            change={(value) => save.mutate({ invert_zoom: value === "back" })}
          />
        </fieldset>
        <div className="flex justify-end border-t pt-3">
          <Button
            size="sm"
            variant="ghost"
            disabled={isDefault || save.isPending}
            onClick={() => save.mutate(defaultCadPreferences)}
          >
            <RotateCcw />
            Restablecer valores predeterminados
          </Button>
        </div>
        {save.isError && (
          <p role="alert" className="mt-2 text-sm text-destructive">
            No se han podido guardar los ajustes. Vuelve a intentarlo.
          </p>
        )}
      </div>
    </section>
  )
}
