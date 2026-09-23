import { DragDropProvider } from "@dnd-kit/react"
import { isSortable, useSortable } from "@dnd-kit/react/sortable"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronRight, GripVertical, Trash2 } from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"

import { type FeaturePublic, FeaturesService } from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { FeaturePartEvidence } from "@/components/Parts/FeaturePartEvidence"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import { PartActions } from "./PartActions"
import { PartIdentityEditor } from "./PartIdentityEditor"
import { featureParts, type PartRow, partRows } from "./parts"
import { SaveStatus } from "./SaveStatus"
import { useAutosave } from "./useAutosave"

/** Cada pieza contiene exclusivamente las cotas de este feature. */
function PartGroup({
  feature,
  row,
  defaultOpen,
  dragHandle,
  editable,
  isNew,
}: {
  feature: FeaturePublic
  row: PartRow
  defaultOpen: boolean
  dragHandle?: ReactNode
  editable?: boolean
  isNew: boolean
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["features"] })
  }

  const unlink = useMutation({
    mutationFn: (partId: string) =>
      FeaturesService.unlinkFeaturePart({ featureId: feature.id, partId }),
    onError: handleError.bind(showErrorToast),
    onSettled: invalidate,
  })

  return (
    <section aria-label={`Pieza ${row.part?.code}`} className="min-w-0">
      <CollapsibleSection
        compact
        className="bg-muted/20"
        leading={dragHandle}
        keepMounted={editable}
        storageKey={`feature-piece:${feature.id}:${row.part?.id ?? "unassigned"}`}
        defaultOpen={defaultOpen}
        headerContent={
          editable && row.part ? (
            <PartIdentityEditor part={row.part} isNew={isNew} />
          ) : undefined
        }
        title={
          row.part ? (
            <span className="flex min-w-0 items-baseline gap-x-2">
              <span className="shrink-0 text-lg font-semibold">
                {row.part.code}
              </span>{" "}
              {row.part.name && (
                <span className="min-w-0 truncate text-muted-foreground">
                  {row.part.name}
                </span>
              )}
            </span>
          ) : (
            // Adjuntos cuya pieza se borro: `part_id` es ON DELETE SET NULL.
            <span className="text-muted-foreground">Sin pieza</span>
          )
        }
        actions={
          <div className="flex shrink-0 items-center gap-1">
            {editable && row.part && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-7 text-destructive"
                title="Quitar esta pieza del feature"
                onClick={() => row.part && unlink.mutate(row.part.id)}
                disabled={unlink.isPending}
              >
                <Trash2 className="size-3.5" />
                <span className="sr-only">Quitar {row.part.code}</span>
              </Button>
            )}
            {row.part && (
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="h-7 shrink-0 gap-1 px-1 text-primary hover:text-primary"
              >
                <Link
                  to="/parts/$partId"
                  params={{ partId: row.part.id }}
                  search={{ feature: feature.id }}
                  title="Ver pieza"
                  aria-label={`Ver pieza ${row.part.code}`}
                >
                  Ver pieza <ChevronRight className="size-4" />
                </Link>
              </Button>
            )}
          </div>
        }
      >
        <div className="border-t pt-2">
          {row.part && (
            <FeaturePartEvidence
              feature={feature}
              partId={row.part.id}
              editable={editable}
            />
          )}
        </div>
      </CollapsibleSection>
    </section>
  )
}

function SortablePart({
  feature,
  row,
  index,
  isNew,
  disabled,
}: {
  feature: FeaturePublic
  row: PartRow
  index: number
  isNew: boolean
  disabled: boolean
}) {
  const { ref, handleRef, isDragging } = useSortable({
    id: row.part!.id,
    index,
    disabled,
    transition: { duration: 220, easing: "ease", idle: true },
  })
  return (
    <div
      ref={ref}
      data-part-id={row.part!.id}
      className={cn(
        "rounded-lg bg-background",
        isDragging && "shadow-xl ring-2 ring-primary/30",
      )}
    >
      <PartGroup
        feature={feature}
        row={row}
        editable
        isNew={isNew}
        defaultOpen={isNew || featureParts(feature).length === 1}
        dragHandle={
          <button
            ref={handleRef}
            type="button"
            disabled={disabled}
            className="touch-none cursor-grab rounded p-0.5 text-muted-foreground hover:bg-accent active:cursor-grabbing"
            aria-label={`Mover pieza ${row.part!.code}`}
          >
            <GripVertical className="size-4" />
          </button>
        }
      />
    </div>
  )
}

/** Piezas y cotas del feature; los documentos se consultan en la ficha de pieza. */
export function PartAssetList({
  feature,
  editable,
  ensureFeatureId,
}: {
  feature: FeaturePublic
  editable?: boolean
  ensureFeatureId?: () => Promise<string>
}) {
  const [newPartId, setNewPartId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const rows = partRows(feature).filter((row) => row.part)
  const signature = rows
    .flatMap((row) => (row.part ? [row.part.id] : []))
    .join(",")
  const server = useMemo(
    () => ({ ids: signature ? signature.split(",") : [] }),
    [signature],
  )
  const reorder = useMutation({
    mutationFn: (ids: string[]) =>
      FeaturesService.reorderFeatureParts({
        featureId: feature.id,
        requestBody: { part_ids: ids },
      }),
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
  const [dragRows, setDragRows] = useState<PartRow[] | null>(null)
  if (editable) {
    const positions = new Map(order.values.ids.map((id, index) => [id, index]))
    rows.sort(
      (a, b) =>
        (positions.get(a.part?.id ?? "") ?? Infinity) -
        (positions.get(b.part?.id ?? "") ?? Infinity),
    )
  }
  const displayRows = dragRows ?? rows
  const footer = editable ? (
    <PartActions
      feature={feature}
      onAdded={setNewPartId}
      ensureFeatureId={ensureFeatureId}
    />
  ) : null

  if (rows.length === 0) {
    return footer ?? null
  }

  return (
    <div className="space-y-3">
      <DragDropProvider
        onDragStart={() => setDragRows(rows)}
        onDragEnd={(event) => {
          if (!event.canceled && isSortable(event.operation.source)) {
            const { initialIndex, index } = event.operation.source
            const ids = displayRows.flatMap((row) =>
              row.part ? [row.part.id] : [],
            )
            if (index !== initialIndex) {
              const [moved] = ids.splice(initialIndex, 1)
              ids.splice(index, 0, moved)
              order.change({ ids })
            }
          }
          setDragRows(null)
        }}
      >
        {displayRows.map((row, index) =>
          editable && row.part ? (
            <SortablePart
              key={row.part.id}
              feature={feature}
              row={row}
              index={index}
              isNew={row.part.id === newPartId}
              disabled={order.saving}
            />
          ) : (
            <PartGroup
              key={row.part?.id ?? "sin-pieza"}
              feature={feature}
              row={row}
              // Con una sola pieza, tenerla cerrada es un clic tonto.
              defaultOpen={rows.length === 1 || row.part?.id === newPartId}
              editable={editable}
              isNew={row.part?.id === newPartId}
            />
          ),
        )}
      </DragDropProvider>
      {editable && (
        <SaveStatus
          error={order.error}
          saving={order.saving}
          retry={order.flush}
        />
      )}
      {footer}
    </div>
  )
}
