import { type AssistantStatus, OpenAPI } from "@/client"
import { type ChatRequest, isSource, type StreamEvent } from "./types"

async function headers() {
  const token =
    typeof OpenAPI.TOKEN === "function"
      ? await OpenAPI.TOKEN({ method: "POST", url: "/api/v1/assistant/chat" })
      : OpenAPI.TOKEN
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token ?? ""}`,
  }
}

function endpoint(path: string) {
  return `${(OpenAPI.BASE || "").replace(/\/$/, "")}/api/v1/assistant/${path}`
}

export async function getStatus(
  signal?: AbortSignal,
): Promise<AssistantStatus> {
  const response = await fetch(endpoint("status"), {
    headers: await headers(),
    signal,
  })
  if (!response.ok) throw new Error("El asistente no está disponible.")
  return response.json()
}

function parseEvent(line: string): StreamEvent {
  const value = JSON.parse(line)
  if (
    ["status", "delta", "error"].includes(value.type) &&
    typeof value.text === "string"
  )
    return value
  if (value.type === "sources" && Array.isArray(value.sources))
    return { type: "sources", sources: value.sources.filter(isSource) }
  if (value.type === "done")
    return { type: "done", truncated: value.truncated === true }
  throw new Error("El asistente ha enviado una respuesta no válida.")
}

export async function streamChat(
  request: ChatRequest,
  signal: AbortSignal,
  onEvent: (event: StreamEvent) => void,
) {
  const response = await fetch(endpoint("chat"), {
    method: "POST",
    headers: await headers(),
    body: JSON.stringify(request),
    signal,
  })
  if ([401, 403].includes(response.status))
    throw new Error("La sesión ha caducado. Vuelve a iniciar sesión.")
  if (response.status === 503) throw new Error("El asistente está desactivado.")
  if (!response.ok || !response.body)
    throw new Error(
      "No se puede conectar con el asistente. Inténtalo de nuevo.",
    )
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ""
  let done = false
  const consume = (line: string) => {
    if (!line.trim()) return
    const event = parseEvent(line)
    if (event.type === "error") throw new Error(event.text)
    if (event.type === "done") done = true
    onEvent(event)
  }
  try {
    while (true) {
      const chunk = await reader.read()
      pending += decoder.decode(chunk.value, { stream: !chunk.done })
      const lines = pending.split("\n")
      pending = lines.pop() ?? ""
      for (const line of lines) consume(line)
      if (pending.length > 100000)
        throw new Error("La respuesta del asistente es demasiado larga.")
      if (chunk.done) break
    }
    consume(pending)
    if (!done)
      throw new Error(
        "Se ha interrumpido la respuesta. Puedes volver a intentarlo.",
      )
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
