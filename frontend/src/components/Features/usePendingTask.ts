import { useCallback, useEffect, useRef, useState } from "react"
import { useEditingSession } from "./EditingSession"

/** Keep an upload in the save boundary until its file reference is stored. */
export function usePendingTask<T>(task: (input: T) => Promise<unknown>) {
  const session = useEditingSession()
  const taskRef = useRef(task)
  taskRef.current = task
  const state = useRef<{
    promise: Promise<boolean> | null
    failed: boolean
    input?: T
  }>({ promise: null, failed: false })
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(false)

  const run = useCallback((input: T): Promise<boolean> => {
    if (state.current.promise) return state.current.promise
    state.current.input = input
    setPending(true)
    const promise = (async () => {
      // Start after the promise is registered, even if a task throws immediately.
      await Promise.resolve()
      try {
        await taskRef.current(input)
        state.current.failed = false
        setError(false)
        return true
      } catch {
        state.current.failed = true
        setError(true)
        return false
      } finally {
        state.current.promise = null
        setPending(false)
      }
    })()
    state.current.promise = promise
    return promise
  }, [])

  const retry = useCallback(() => run(state.current.input as T), [run])
  useEffect(
    () =>
      session?.register({
        pending: () => Boolean(state.current.promise) || state.current.failed,
        flush: async () =>
          state.current.promise
            ? await state.current.promise
            : !state.current.failed,
      }),
    [session],
  )

  return { run, retry, pending, error }
}
