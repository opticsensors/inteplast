import { skipToken, useQuery } from "@tanstack/react-query"
import { useCallback, useLayoutEffect, useRef } from "react"
import type { CadPreferences, CurrentUserPublic } from "@/client"

export type ViewerPreferences = Required<CadPreferences>
export const defaultCadPreferences: ViewerPreferences = {
  cad_projection: "orthographic",
  cad_controls: "solidworks",
  invert_zoom: false,
}

// The authenticated layout already loads /users/me. Subscribe to that account
// without fetching anything when a CAD opens or a preference changes.
export function useConfigureCadViewer() {
  const { data: user } = useQuery<CurrentUserPublic>({
    queryKey: ["currentUser"],
    queryFn: skipToken,
  })
  const preferences = useRef(defaultCadPreferences)
  type Controller = { setPreferences: (value: ViewerPreferences) => void }
  const controller = useRef<Controller | null>(null)
  const { cad_projection, cad_controls, invert_zoom } =
    user ?? defaultCadPreferences
  useLayoutEffect(() => {
    preferences.current = {
      cad_projection: cad_projection ?? defaultCadPreferences.cad_projection,
      cad_controls: cad_controls ?? defaultCadPreferences.cad_controls,
      invert_zoom: invert_zoom ?? defaultCadPreferences.invert_zoom,
    }
    controller.current?.setPreferences(preferences.current)
  }, [cad_projection, cad_controls, invert_zoom])
  return useCallback((next: Controller | null) => {
    controller.current = next
    next?.setPreferences(preferences.current)
  }, [])
}
