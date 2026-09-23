import {
  ArrowUp,
  ChevronDown,
  ChevronUp,
  MessageCircle,
  Plus,
  Square,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { RichTextView } from "@/components/Common/RichText"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useAssistant } from "./useAssistant"

export default function AssistantWidget() {
  const [mode, setMode] = useState<"closed" | "open" | "minimized">("closed")
  const [draft, setDraft] = useState("")
  const { turns, busy, status, send, reset, stop } = useAssistant()
  const input = useRef<HTMLTextAreaElement>(null)
  const toggle = useRef<HTMLButtonElement>(null)
  const scroll = useRef<HTMLDivElement>(null)
  const following = useRef(true)
  const opened = useRef(false)
  const last = turns[turns.length - 1]

  useEffect(() => {
    if (mode === "open") {
      opened.current = true
      input.current?.focus()
    } else if (opened.current) toggle.current?.focus()
  }, [mode])
  // Content changes affect scrollHeight; keep position when reading earlier turns.
  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll follows rendered content changes.
  useEffect(() => {
    if (following.current && scroll.current)
      scroll.current.scrollTop = scroll.current.scrollHeight
  }, [last?.answer, last?.error, turns.length, status, mode])

  function submit() {
    if (!draft.trim() || busy) return
    const question = draft
    setDraft("")
    following.current = true
    void send(question)
  }

  if (mode === "closed")
    return (
      <Button
        ref={toggle}
        className="fixed bottom-4 right-4 z-40 h-11 gap-2 rounded-full shadow-lg"
        onClick={() => setMode("open")}
        aria-expanded={false}
        aria-controls="assistant-chat"
      >
        <MessageCircle className="size-4" /> Asistente
      </Button>
    )

  return (
    <section
      id="assistant-chat"
      aria-label="Asistente"
      className={`fixed bottom-4 right-4 z-40 flex max-w-[calc(100vw-2rem)] flex-col overflow-hidden border bg-background shadow-xl ${mode === "open" ? "h-[min(580px,calc(100dvh-2rem))] w-[400px] rounded-xl" : "h-11 w-max rounded-full"}`}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation()
          setMode("minimized")
        }
      }}
    >
      <header
        className={`flex shrink-0 items-center bg-muted/50 ${mode === "open" ? "gap-2 border-b px-3 py-2" : "h-full gap-1 pl-3 pr-2"}`}
      >
        <MessageCircle
          className={`size-4 shrink-0 text-primary ${mode === "minimized" && busy ? "animate-pulse motion-reduce:animate-none" : ""}`}
        />
        <button
          ref={toggle}
          type="button"
          className="min-w-0 flex-1 whitespace-nowrap text-left text-sm font-semibold"
          onClick={() => setMode(mode === "open" ? "minimized" : "open")}
          aria-expanded={mode === "open"}
          aria-label={
            mode === "open" ? "Minimizar asistente" : "Expandir asistente"
          }
        >
          Asistente
          {mode === "minimized" && busy && (
            <span className="sr-only">Consultando…</span>
          )}
        </button>
        {mode === "open" && (
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            aria-label="Nueva conversación"
            title="Nueva conversación"
            onClick={() => {
              reset()
              setDraft("")
              input.current?.focus()
            }}
          >
            <Plus className="size-4" />
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          aria-label={mode === "open" ? "Minimizar chat" : "Expandir chat"}
          onClick={() => setMode(mode === "open" ? "minimized" : "open")}
        >
          {mode === "open" ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronUp className="size-4" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          aria-label="Cerrar asistente"
          onClick={() => setMode("closed")}
        >
          <X className="size-4" />
        </Button>
      </header>
      {mode === "open" && (
        <>
          <div
            ref={scroll}
            role="log"
            aria-label="Conversación"
            aria-live="off"
            className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain p-4"
            onScroll={(event) => {
              const el = event.currentTarget
              following.current =
                el.scrollHeight - el.scrollTop - el.clientHeight < 60
            }}
          >
            {turns.length === 0 && (
              <p className="py-4 text-sm leading-relaxed text-muted-foreground">
                Consulta el conocimiento de Inteplast, pregunta por piezas,
                features, notas, mediciones o retoques.
              </p>
            )}
            {turns.map((turn) => (
              <div key={turn.id} className="space-y-3">
                <div className="ml-6 rounded-xl rounded-br-sm bg-muted px-3 py-2 text-sm whitespace-pre-wrap break-words">
                  {turn.question}
                </div>
                <div className="space-y-2 pr-2">
                  {turn.answer && (
                    <RichTextView
                      value={turn.answer}
                      className="break-words [overflow-wrap:anywhere]"
                    />
                  )}
                  {turn.sources.length > 0 && (
                    <section
                      className="flex flex-wrap gap-1.5"
                      aria-label="Fuentes consultadas"
                    >
                      {turn.sources.map((source) => (
                        <a
                          key={source.url}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="max-w-full truncate rounded-md border px-2 py-1 text-xs text-primary hover:bg-muted"
                          title={`${source.label} (abre otra pestaña)`}
                        >
                          {source.label}
                        </a>
                      ))}
                    </section>
                  )}
                  {turn.truncated && (
                    <p className="text-xs text-muted-foreground">
                      Se ha alcanzado el límite de respuesta. Pide que continúe
                      para ampliar.
                    </p>
                  )}
                  {turn.error && (
                    <p role="alert" className="text-sm text-destructive">
                      {turn.error}
                    </p>
                  )}
                  {turn.id === last?.id && turn.error && !busy && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void send(turn.question, true)}
                    >
                      Volver a intentar
                    </Button>
                  )}
                </div>
              </div>
            ))}
            <output className="block text-xs text-muted-foreground">
              {busy ? status : last?.complete ? "Respuesta completada." : ""}
            </output>
          </div>
          <form
            className="shrink-0 space-y-2 border-t p-3"
            onSubmit={(event) => {
              event.preventDefault()
              submit()
            }}
          >
            <div className="flex items-end gap-2">
              <Textarea
                ref={input}
                aria-label="Pregunta al asistente"
                placeholder="Escribe tu pregunta…"
                value={draft}
                maxLength={2000}
                rows={2}
                className="min-h-16 max-h-32 resize-none text-sm"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault()
                    submit()
                  }
                }}
              />
              {busy ? (
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  aria-label="Detener respuesta"
                  onClick={stop}
                >
                  <Square className="size-4" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="icon"
                  aria-label="Enviar pregunta"
                  disabled={!draft.trim()}
                >
                  <ArrowUp className="size-4" />
                </Button>
              )}
            </div>
          </form>
        </>
      )}
    </section>
  )
}
