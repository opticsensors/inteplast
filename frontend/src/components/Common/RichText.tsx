import { Bold, Code, Italic, List } from "lucide-react"
import { Fragment, type ReactNode, useRef } from "react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

/**
 * Editor y visor de texto con formato ligero para warnings y lessons learned.
 *
 * El cuerpo se guarda como markdown reducido: **negrita**, *cursiva*, `codigo`
 * y listas con guion. Es a proposito: sin dependencias nuevas, sin HTML que
 * sanear, y el dia que haga falta un editor completo (TipTap) el campo del
 * backend no cambia, solo se sustituye este componente.
 */

const INLINE = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g

function renderInline(text: string): ReactNode[] {
  return text.split(INLINE).map((chunk, index) => {
    const key = `${index}-${chunk}`
    if (chunk.startsWith("**") && chunk.endsWith("**")) {
      return <strong key={key}>{chunk.slice(2, -2)}</strong>
    }
    if (chunk.startsWith("`") && chunk.endsWith("`")) {
      return (
        <code key={key} className="rounded bg-muted px-1 py-0.5 text-xs">
          {chunk.slice(1, -1)}
        </code>
      )
    }
    if (chunk.startsWith("*") && chunk.endsWith("*")) {
      return <em key={key}>{chunk.slice(1, -1)}</em>
    }
    return <Fragment key={key}>{chunk}</Fragment>
  })
}

export function RichTextView({
  value,
  className,
}: {
  value: string | null | undefined
  className?: string
}) {
  if (!value) return null

  // Se agrupan las lineas consecutivas que empiezan por guion en una lista
  const blocks: { type: "list" | "text"; lines: string[] }[] = []
  for (const line of value.split("\n")) {
    const isItem = /^\s*[-*]\s+/.test(line)
    const type = isItem ? "list" : "text"
    const last = blocks[blocks.length - 1]
    if (last?.type === type) {
      last.lines.push(line)
    } else {
      blocks.push({ type, lines: [line] })
    }
  }

  return (
    <div className={cn("space-y-2 text-sm", className)}>
      {blocks.map((block, blockIndex) =>
        block.type === "list" ? (
          <ul key={blockIndex} className="list-disc space-y-1 pl-5">
            {block.lines.map((line, lineIndex) => (
              <li key={lineIndex}>
                {renderInline(line.replace(/^\s*[-*]\s+/, ""))}
              </li>
            ))}
          </ul>
        ) : (
          <p key={blockIndex} className="whitespace-pre-wrap">
            {renderInline(block.lines.join("\n"))}
          </p>
        ),
      )}
    </div>
  )
}

interface RichTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function RichTextEditor({
  value,
  onChange,
  placeholder,
}: RichTextEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const wrap = (marker: string) => {
    const textarea = textareaRef.current
    if (!textarea) return
    const { selectionStart: start, selectionEnd: end } = textarea
    const selected = value.slice(start, end) || "texto"
    onChange(
      `${value.slice(0, start)}${marker}${selected}${marker}${value.slice(end)}`,
    )
    textarea.focus()
  }

  const prefixLine = (prefix: string) => {
    const textarea = textareaRef.current
    if (!textarea) return
    const start = value.lastIndexOf("\n", textarea.selectionStart - 1) + 1
    onChange(`${value.slice(0, start)}${prefix}${value.slice(start)}`)
    textarea.focus()
  }

  const tools = [
    { icon: Bold, label: "Negrita", action: () => wrap("**") },
    { icon: Italic, label: "Cursiva", action: () => wrap("*") },
    { icon: Code, label: "Codigo", action: () => wrap("`") },
    { icon: List, label: "Lista", action: () => prefixLine("- ") },
  ]

  return (
    <div className="rounded-md border">
      <div className="flex items-center gap-1 border-b px-1 py-1">
        {tools.map((tool) => (
          <Button
            key={tool.label}
            type="button"
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={tool.action}
          >
            <tool.icon className="size-4" />
            <span className="sr-only">{tool.label}</span>
          </Button>
        ))}
      </div>
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="min-h-40 rounded-none border-0 shadow-none focus-visible:ring-0"
      />
    </div>
  )
}
