import { useEffect, useRef, useState } from "react"
import { streamChat } from "./api"
import type { ChatRequest, ChatTurn } from "./types"

function history(turns: ChatTurn[], question: string): ChatRequest["messages"] {
  const messages: ChatRequest["messages"] = []
  let size = question.length
  for (const turn of turns
    .filter((turn) => turn.complete)
    .slice(-4)
    .reverse()) {
    // Keep the full answer on screen. A long answer must not discard its
    // question (and therefore the selected piece) from the next request.
    const answer =
      turn.answer.length > 3000
        ? `${turn.answer.slice(0, 2900)}\n[Respuesta anterior abreviada en el historial.]`
        : turn.answer
    if (size + turn.question.length + answer.length > 12000) break
    size += turn.question.length + answer.length
    messages.unshift(
      { role: "user", content: turn.question },
      { role: "assistant", content: answer },
    )
  }
  return [...messages, { role: "user", content: question }]
}

export function useAssistant() {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState("")
  const active = useRef<AbortController | null>(null)
  const nextId = useRef(0)
  useEffect(() => () => active.current?.abort(), [])

  const send = async (rawQuestion: string, retry = false) => {
    const question = rawQuestion.trim()
    if (!question || active.current) return
    const previous = retry ? turns.slice(0, -1) : turns
    const id = `turn-${nextId.current++}`
    const controller = new AbortController()
    active.current = controller
    setTurns([
      ...previous.slice(-29),
      { id, question, answer: "", sources: [], complete: false },
    ])
    setBusy(true)
    setStatus("Preparando respuesta…")
    const update = (
      change: Partial<ChatTurn> | ((turn: ChatTurn) => Partial<ChatTurn>),
    ) => {
      if (active.current !== controller) return
      setTurns((current) =>
        current.map((turn) =>
          turn.id === id
            ? {
                ...turn,
                ...(typeof change === "function" ? change(turn) : change),
              }
            : turn,
        ),
      )
    }
    try {
      await streamChat(
        { messages: history(previous, question) },
        controller.signal,
        (event) => {
          if (active.current !== controller) return
          if (event.type === "delta")
            update((turn) => ({ answer: turn.answer + event.text }))
          if (event.type === "status") setStatus(event.text)
          if (event.type === "sources") update({ sources: event.sources })
          if (event.type === "done")
            update({ complete: true, truncated: event.truncated })
        },
      )
    } catch (error) {
      update({
        complete: false,
        error: controller.signal.aborted
          ? "Respuesta detenida."
          : error instanceof Error
            ? error.message
            : "No se ha podido completar la consulta.",
      })
    } finally {
      if (active.current === controller) {
        active.current = null
        setBusy(false)
        setStatus("")
      }
    }
  }

  const reset = () => {
    active.current?.abort()
    active.current = null
    setBusy(false)
    setStatus("")
    setTurns([])
  }
  return {
    turns,
    busy,
    status,
    send,
    reset,
    stop: () => active.current?.abort(),
  }
}
