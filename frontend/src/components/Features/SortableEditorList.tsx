import { DragDropProvider } from "@dnd-kit/react"
import { isSortable, useSortable } from "@dnd-kit/react/sortable"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { GripVertical } from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"

import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import { SaveStatus } from "./SaveStatus"
import { useAutosave } from "./useAutosave"

function SortableEditorItem({
  id,
  index,
  label,
  disabled,
  children,
}: {
  id: string
  index: number
  label: string
  disabled: boolean
  children: (handle: ReactNode) => ReactNode
}) {
  const { ref, handleRef, isDragging } = useSortable({
    id,
    index,
    disabled,
    transition: { duration: 220, easing: "ease", idle: true },
  })
  return (
    <div
      ref={ref}
      data-sortable-id={id}
      className={cn(
        "rounded-md bg-background",
        isDragging && "shadow-xl ring-2 ring-primary/30",
      )}
    >
      {children(
        <button
          ref={handleRef}
          type="button"
          disabled={disabled}
          className="shrink-0 touch-none cursor-grab rounded p-0.5 text-muted-foreground hover:bg-accent active:cursor-grabbing"
          aria-label={label}
        >
          <GripVertical className="size-4" />
        </button>,
      )}
    </div>
  )
}

/** Each list owns its drag context: files stay in their piece, notes in their section. */
export function SortableEditorList<T extends { id: string }>({
  items,
  saveOrder,
  dragLabel,
  children,
}: {
  items: T[]
  saveOrder: (ids: string[]) => Promise<unknown>
  dragLabel: (item: T) => string
  children: (item: T, handle: ReactNode) => ReactNode
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const signature = items.map((item) => item.id).join(",")
  const server = useMemo(
    () => ({ ids: signature ? signature.split(",") : [] }),
    [signature],
  )
  const reorder = useMutation({
    mutationFn: saveOrder,
    onError: handleError.bind(showErrorToast),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["features"] }),
  })
  const order = useAutosave(server, (patch) => {
    const current = new Set(server.ids)
    const ids = (patch.ids ?? server.ids).filter((id) => current.has(id))
    return reorder.mutateAsync([
      ...ids,
      ...server.ids.filter((id) => !ids.includes(id)),
    ])
  })
  const positions = new Map(order.values.ids.map((id, index) => [id, index]))
  const sorted = [...items].sort(
    (a, b) =>
      (positions.get(a.id) ?? Infinity) - (positions.get(b.id) ?? Infinity),
  )
  // dnd-kit moves the DOM while dragging. Freeze the React list until drop so
  // background refetches cannot fight the animated placeholder.
  const [dragItems, setDragItems] = useState<T[] | null>(null)
  const displayed = dragItems ?? sorted

  return (
    <>
      <DragDropProvider
        onDragStart={() => setDragItems(sorted)}
        onDragEnd={(event) => {
          if (!event.canceled && isSortable(event.operation.source)) {
            const { initialIndex, index } = event.operation.source
            if (index !== initialIndex) {
              const ids = displayed.map((item) => item.id)
              const [moved] = ids.splice(initialIndex, 1)
              ids.splice(index, 0, moved)
              order.change({ ids })
            }
          }
          setDragItems(null)
        }}
      >
        {displayed.map((item, index) => (
          <SortableEditorItem
            key={item.id}
            id={item.id}
            index={index}
            label={dragLabel(item)}
            disabled={order.saving}
          >
            {(handle) => children(item, handle)}
          </SortableEditorItem>
        ))}
      </DragDropProvider>
      <SaveStatus
        error={order.error}
        saving={order.saving}
        retry={order.flush}
      />
    </>
  )
}
