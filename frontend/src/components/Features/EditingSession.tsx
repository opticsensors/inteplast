import { createContext, useContext, useState } from "react"

export interface PendingEdit {
  pending: () => boolean
  flush: () => Promise<boolean>
}

/** One save boundary for all editors, including editors in folded sections. */
export class EditingSession {
  private editors = new Set<PendingEdit>()

  register(editor: PendingEdit) {
    this.editors.add(editor)
    return () => {
      this.editors.delete(editor)
    }
  }

  pending = () => [...this.editors].some((editor) => editor.pending())

  flush = async () => {
    const results = await Promise.all(
      [...this.editors].map((editor) => editor.flush()),
    )
    return results.every(Boolean)
  }
}

export const EditingSessionContext = createContext<EditingSession | null>(null)

export function useEditingSession() {
  return useContext(EditingSessionContext)
}

export function useNewEditingSession() {
  return useState(() => new EditingSession())[0]
}
