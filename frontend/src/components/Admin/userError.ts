import { ApiError } from "@/client"

export function userError(error: Error): string {
  if (error instanceof ApiError) {
    const body = error.body
    const detail =
      body && typeof body === "object" && "detail" in body
        ? body.detail
        : undefined
    if (typeof detail === "string" && detail.includes("email already exists")) {
      return "Ya existe una cuenta con ese correo."
    }
    if (error.status === 404) return "No se encuentra la cuenta."
    if (error.status === 403)
      return "No tienes permiso para realizar esta acción."
    if (error.status === 422) return "Revisa los datos de la cuenta."
  }
  return "No se ha podido completar la operación. Vuelve a intentarlo."
}
