import { useState } from "react"
import { createRoot } from "react-dom/client"
import AssistantWidget from "@/assistant/AssistantWidget"
import { OpenAPI } from "@/client"

OpenAPI.BASE = "http://component.invalid"
OpenAPI.TOKEN = "test-session"
window.assistantRequests = []
window.fetch = async (_url, init) => {
  window.assistantRequests.push(JSON.parse(init.body))
  if (window.assistantOffline) throw new Error("Sin conexión")
  const stream = new ReadableStream({
    start(controller) {
      window.assistantEmit = (events, finish = true) => {
        const bytes = new TextEncoder().encode(
          events.map((event) => JSON.stringify(event)).join("\n") + "\n",
        )
        // Include boundaries inside UTF-8 characters, JSON tokens and NDJSON lines.
        for (let n = 0; n < bytes.length; n += 3)
          controller.enqueue(bytes.slice(n, n + 3))
        if (finish) controller.close()
      }
      init.signal.addEventListener("abort", () =>
        controller.error(new DOMException("Aborted", "AbortError")),
      )
    },
  })
  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson" },
  })
}

function App() {
  const [page, setPage] = useState(window.location.pathname)
  window.assistantNavigate = (url) => {
    window.history.pushState({}, "", url)
    setPage(url)
  }
  return (
    <div data-page={page}>
      <AssistantWidget />
    </div>
  )
}
createRoot(document.getElementById("root")).render(<App />)
