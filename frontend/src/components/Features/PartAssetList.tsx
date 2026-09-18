import { DragDropProvider } from "@dnd-kit/react"
import { isSortable, useSortable } from "@dnd-kit/react/sortable"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Download, GripVertical, Plus, Trash2 } from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"

import {
  type FeatureAssetPublic,
  type FeaturePublic,
  FeaturesService,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { FileLink } from "@/components/Common/FileLink"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { formatFileSize, handleError } from "@/utils"
import { AssetEditRow, NEW_ASSET_NAME } from "./AssetEditRow"
import { ASSET_ICONS, ASSET_KIND_SHORT, ASSET_KINDS } from "./constants"
import { DocumentStatus } from "./DocumentStatus"
import { PartActions } from "./PartActions"
import { PartIdentityEditor } from "./PartIdentityEditor"
import { assetName, featureParts, type PartRow, partRows } from "./parts"
import { SaveStatus } from "./SaveStatus"
import { SortableEditorList } from "./SortableEditorList"
import { useAutosave } from "./useAutosave"
import { fileAction } from "./viewers"

/** El orden elegido se conserva tambien en la ficha de lectura. */
const assetsOf = (row: PartRow) =>
  ASSET_KINDS.flatMap((kind) => row.assets[kind]).sort(
    (a, b) => (a.position ?? 0) - (b.position ?? 0),
  )

/**
 * Una fila = un fichero, en modo lectura.
 *
 * 🔑 Lo que la fila promete es lo que va a pasar: si hay visor, clicarla lleva
 * a la pagina del fichero; si no lo hay, se dice en gris por que (que programa
 * hace falta, o que es demasiado grande) y solo queda descargar.
 */
function AssetRow({
  featureId,
  asset,
}: {
  featureId: string
  asset: FeatureAssetPublic
}) {
  const Icon = ASSET_ICONS[asset.kind]
  const file = asset.file
  const name = assetName(asset)
  const { action, reason } = fileAction(file)

  const body = (
    <>
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <span className="w-16 shrink-0 text-xs uppercase tracking-wide text-muted-foreground">
        {ASSET_KIND_SHORT[asset.kind]}
      </span>
      <span className="min-w-0 flex-1 truncate" title={name}>
        {name}
      </span>
      {file ? (
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatFileSize(file.size)}
        </span>
      ) : (
        <span className="shrink-0 text-xs italic text-muted-foreground">
          sin archivo vinculado
        </span>
      )}
    </>
  )

  return (
    <div className="rounded-md border">
      <div className="flex items-center gap-2 px-2 py-1.5 text-sm">
        {file ? (
          <Link
            to="/features/$featureId/fichero/$assetId"
            params={{ featureId, assetId: asset.id }}
            className="flex min-w-0 flex-1 items-center gap-2 hover:underline"
            title={action === "view" ? `Ver ${name}` : `Detalles de ${name}`}
          >
            {body}
          </Link>
        ) : (
          <div className="flex min-w-0 flex-1 items-center gap-2">{body}</div>
        )}

        {file && (
          <Button
            asChild
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            title={`Descargar ${name}`}
          >
            <FileLink fileId={file.id} downloadFile download={file.filename}>
              <Download className="size-3.5" />
              <span className="sr-only">Descargar {name}</span>
            </FileLink>
          </Button>
        )}
      </div>

      <DocumentStatus file={file} />

      {reason && (
        <p className="px-2 pb-1.5 pl-8 text-xs text-muted-foreground">
          {reason}
        </p>
      )}
    </div>
  )
}

/** Una pieza y sus ficheros: el sub-desplegable. */
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
  const [newAssetId, setNewAssetId] = useState<string | null>(null)
  const assets = assetsOf(row)
  const uploaded = assets.filter((asset) => asset.file).length

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["features"] })
  }

  // Anadir no abre ninguna modal: crea la fila y la deja lista para escribir
  // encima. El tipo y el nombre se corrigen ahi mismo, o los rellena el
  // fichero cuando se sube.
  const create = useMutation({
    mutationFn: () =>
      FeaturesService.createFeatureAsset({
        featureId: feature.id,
        requestBody: {
          kind: "mold",
          name: NEW_ASSET_NAME,
          part_id: row.part?.id ?? null,
          position:
            Math.max(
              -1,
              ...(feature.assets ?? []).map((asset) => asset.position ?? 0),
            ) + 1,
        },
      }),
    onSuccess: (created) => setNewAssetId(created.id),
    onError: handleError.bind(showErrorToast),
    onSettled: invalidate,
  })

  const unlink = useMutation({
    mutationFn: (partId: string) =>
      FeaturesService.unlinkFeaturePart({ featureId: feature.id, partId }),
    onError: handleError.bind(showErrorToast),
    onSettled: invalidate,
  })

  return (
    <CollapsibleSection
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
          <span className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-mono font-semibold">{row.part.code}</span>{" "}
            {row.part.name && (
              <span className="text-muted-foreground">{row.part.name}</span>
            )}
          </span>
        ) : (
          // Adjuntos cuya pieza se borro: `part_id` es ON DELETE SET NULL.
          <span className="text-muted-foreground">Sin pieza</span>
        )
      }
      actions={
        <div className="flex shrink-0 items-center gap-1">
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {assets.length} fichero{assets.length === 1 ? "" : "s"} · {uploaded}{" "}
            vinculado{uploaded === 1 ? "" : "s"}
          </span>
          {editable && row.part && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7 text-destructive"
              title="Quitar esta pieza y sus adjuntos del feature"
              onClick={() => row.part && unlink.mutate(row.part.id)}
              disabled={unlink.isPending}
            >
              <Trash2 className="size-3.5" />
              <span className="sr-only">Quitar {row.part.code}</span>
            </Button>
          )}
        </div>
      }
    >
      {editable ? (
        <SortableEditorList
          items={assets}
          saveOrder={(ids) =>
            FeaturesService.reorderFeatureAssets({
              featureId: feature.id,
              requestBody: { part_id: row.part?.id ?? null, asset_ids: ids },
            })
          }
          dragLabel={(asset) => `Mover fichero ${assetName(asset)}`}
        >
          {(asset, handle) => (
            <AssetEditRow
              asset={asset}
              isNew={asset.id === newAssetId}
              dragHandle={handle}
            />
          )}
        </SortableEditorList>
      ) : (
        assets.map((asset) => (
          <AssetRow key={asset.id} featureId={feature.id} asset={asset} />
        ))
      )}
      {editable && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => create.mutate()}
          disabled={create.isPending}
        >
          <Plus className="mr-1 size-3.5" />
          Anadir fichero
        </Button>
      )}
    </CollapsibleSection>
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

/**
 * Los ficheros del feature, **agrupados por pieza**: un desplegable por pieza y
 * dentro una fila por fichero.
 *
 * Antes esto era una tabla de pieza x tipo de fichero. Se cambio el 2026-08-25
 * por tres motivos: era lo unico con forma de tabla en toda la ficha, en la
 * casilla no cabe el nombre del fichero —que es lo que se quiere leer—, y con
 * varias piezas se iba en horizontal. El checklist de lo que falta no se
 * pierde: lo dan el contador de cada pieza y las filas «sin archivo vinculado».
 *
 * 🔑 El MISMO componente sirve la ficha (lectura) y el formulario (edicion).
 * En edicion cada fila se escribe encima —tipo, nombre y fichero— sin botones
 * de editar. El selector de originales externos usa un dialogo.
 */
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
  const rows = partRows(feature)
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

  const assets = feature.assets ?? []
  const uploaded = assets.filter((asset) => asset.file).length
  const pieces = rows.filter((row) => row.part).length

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {pieces} pieza{pieces === 1 ? "" : "s"} · {assets.length} fichero
        {assets.length === 1 ? "" : "s"} · {uploaded} vinculado
        {uploaded === 1 ? "" : "s"}
      </p>
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
