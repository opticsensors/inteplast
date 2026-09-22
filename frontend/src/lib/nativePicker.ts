/** A cancelled Windows dialog returns null and never changes the current link. */
export async function pickNativePath(
  kind: "folder" | "file",
  signal?: AbortSignal,
): Promise<string | null> {
  const response = await fetch("/__native-picker", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
    },
    body: JSON.stringify({ kind }),
    signal: AbortSignal.any([
      signal ?? new AbortController().signal,
      AbortSignal.timeout(310000),
    ]),
  })
  if (!response.headers.get("content-type")?.includes("application/json"))
    throw new Error(
      "El selector de Windows está disponible al abrir la instalación local de la aplicación.",
    )
  const data = await response.json()
  if (!response.ok)
    throw new Error(data.detail ?? "No se pudo abrir el selector de Windows.")
  return data.path
}
