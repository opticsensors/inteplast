import { useCallback, useEffect, useRef, useState } from "react"

import { useEditingSession } from "./EditingSession"

/** Save only fields changed by this editor, in order, retaining failed drafts. */
export function useAutosave<T extends Record<string, unknown>>(
  server: T,
  persist: (patch: Partial<T>) => Promise<unknown>,
  valid: (values: T) => boolean = () => true,
  delayMs: number | null = 700,
) {
  const session = useEditingSession()
  const [values, setValues] = useState(server)
  const [error, setError] = useState(false)
  const [saving, setSaving] = useState(false)
  const draft = useRef(server)
  const changed = useRef(new Map<keyof T, number>())
  const version = useRef(0)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const running = useRef<Promise<boolean> | null>(null)
  const persistRef = useRef(persist)
  const validRef = useRef(valid)
  persistRef.current = persist
  validRef.current = valid

  useEffect(() => {
    const next = { ...draft.current }
    for (const key of Object.keys(server) as (keyof T)[]) {
      if (!changed.current.has(key)) next[key] = server[key]
    }
    draft.current = next
    setValues(next)
  }, [server])

  const flush = useCallback(async (): Promise<boolean> => {
    clearTimeout(timer.current)
    if (running.current) return running.current
    const save = async () => {
      while (changed.current.size) {
        if (!validRef.current(draft.current)) {
          setError(true)
          return false
        }
        const revisions = new Map(changed.current)
        const patch: Partial<T> = {}
        for (const key of revisions.keys()) patch[key] = draft.current[key]
        setSaving(true)
        try {
          await persistRef.current(patch)
        } catch {
          setError(true)
          return false
        } finally {
          setSaving(false)
        }
        for (const [key, revision] of revisions) {
          if (changed.current.get(key) === revision) changed.current.delete(key)
        }
        setError(false)
      }
      return true
    }
    running.current = save()
    try {
      return await running.current
    } finally {
      running.current = null
    }
  }, [])

  const change = useCallback(
    (patch: Partial<T>) => {
      draft.current = { ...draft.current, ...patch }
      for (const key of Object.keys(patch) as (keyof T)[]) {
        changed.current.set(key, ++version.current)
      }
      setValues(draft.current)
      clearTimeout(timer.current)
      if (delayMs !== null)
        timer.current = setTimeout(() => {
          void flush()
        }, delayMs)
    },
    [flush, delayMs],
  )

  const pending = useCallback(
    () => changed.current.size > 0 || running.current !== null,
    [],
  )

  useEffect(
    () => session?.register({ pending, flush }),
    [session, pending, flush],
  )
  useEffect(
    () => () => {
      clearTimeout(timer.current)
    },
    [],
  )

  return { values, change, flush, pending, error, saving }
}
