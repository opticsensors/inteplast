import { createContext, useState } from "react"
import type { CorrectionText } from "@/client"

export function sameInterval(
  a: CorrectionText,
  b: Omit<CorrectionText, "text" | "action">,
) {
  return (
    a.revision === b.revision &&
    a.cota === b.cota &&
    a.before === b.before &&
    a.after === b.after
  )
}

export function sameCorrection(
  a: CorrectionText,
  b: Omit<CorrectionText, "text">,
) {
  return a.action === b.action && sameInterval(a, b)
}

export function useCorrectionTextDrafts() {
  const [drafts, setDrafts] = useState<CorrectionText[]>([])
  function change(next: CorrectionText, savedText: string) {
    setDrafts((previous) => {
      const others = previous.filter((item) => !sameCorrection(item, next))
      return next.text === savedText ? others : [...others, next]
    })
  }
  return { drafts, change }
}

export const CorrectionEditor = createContext<
  (ReturnType<typeof useCorrectionTextDrafts> & { disabled: boolean }) | null
>(null)
