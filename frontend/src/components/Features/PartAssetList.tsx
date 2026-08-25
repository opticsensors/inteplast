import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Download, Plus, Trash2 } from "lucide-react"
import { type ReactNode, useState } from "react"

import {
  type FeatureAssetPublic,
  type FeaturePublic,
  FeaturesService,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { fileUrl, formatFileSize, handleError } from "@/utils"
import { AssetEditRow, NEW_ASSET_NAME } from "./AssetEditRow"
import { ASSET_ICONS, ASSET_KIND_SHORT, ASSET_KINDS } from "./constants"
import { featureParts, type PartRow, partRows } from "./parts"
import { fileAction } from "./viewers"

/** Los adjuntos de una pieza, en el orden de los tipos, aplanados. */
const assetsOf = (row: PartRow) =>
  ASSET_KINDS.flatMap((kind) => row.assets[kind])

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
  const { action, reason } = fileAction(file)

  const body = (
    <>
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <span className="w-16 shrink-0 text-xs uppercase tracking-wide text-muted-foreground">
        {ASSET_KIND_SHORT[asset.kind]}
      </span>
      <span className="min-w-0 flex-1 truncate">{asset.name}</span>
      {file ? (
        <span
          className="hidden shrink-0 text-xs text-muted-foreground sm:inline"
          title={file.filename}
        >
          {file.filename} · {formatFileSize(file.size)}
        </span>
      ) : (
        <span className="shrink-0 text-xs italic text-muted-foreground">
          sin fichero subido
        </span>
      )}
    </>
  )

  return (
    <div className="rounded-md border">
      <div className="flex items-center gap-2 px-2 py-1.5 text-sm">
        {file && action === "view" ? (
          <Link
            to="/features/$featureId/fichero/$assetId"
            params={{ featureId, assetId: asset.id }}
            className="flex min-w-0 flex-1 items-center gap-2 hover:underline"
            title={`Ver ${asset.name}`}
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
            title={`Descargar ${file.filename}`}
          >
            <a href={fileUrl(file.id)} download={file.filename}>
              <Download className="size-3.5" />
              <span className="sr-only">Descargar {asset.name}</span>
            </a>
          </Button>
        )}
      </div>

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
  declared,
  editable,
}: {
  feature: FeaturePublic
  row: PartRow
  defaultOpen: boolean
  /** La pieza esta en `feature.parts`, no solo aportando ficheros. */
  declared: boolean
  editable?: boolean
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
      defaultOpen={defaultOpen}
      title={
        row.part ? (
          <span className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-mono font-semibold">{row.part.code}</span>
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
          <span className="text-xs text-muted-foreground">
            {assets.length} fichero{assets.length === 1 ? "" : "s"} · {uploaded}{" "}
            subido{uploaded === 1 ? "" : "s"}
          </span>
          {editable && declared && row.part && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7 text-destructive"
              title="Quitar la pieza. Sus ficheros no se borran, y si los hay la pieza se sigue viendo."
              onClick={() => row.part && unlink.mutate(row.part.id)}
            >
              <Trash2 className="size-3.5" />
              <span className="sr-only">Quitar {row.part.code}</span>
            </Button>
          )}
        </div>
      }
    >
      {assets.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Todavia no hay ningun fichero de esta pieza.
        </p>
      )}
      {assets.map((asset) =>
        editable ? (
          <AssetEditRow
            key={asset.id}
            asset={asset}
            parts={featureParts(feature)}
            isNew={asset.id === newAssetId}
          />
        ) : (
          <AssetRow key={asset.id} featureId={feature.id} asset={asset} />
        ),
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

/**
 * Los ficheros del feature, **agrupados por pieza**: un desplegable por pieza y
 * dentro una fila por fichero.
 *
 * Antes esto era una tabla de pieza x tipo de fichero. Se cambio el 2026-08-25
 * por tres motivos: era lo unico con forma de tabla en toda la ficha, en la
 * casilla no cabe el nombre del fichero —que es lo que se quiere leer—, y con
 * varias piezas se iba en horizontal. El checklist de lo que falta no se
 * pierde: lo dan el contador de cada pieza y las filas «sin fichero subido».
 *
 * 🔑 El MISMO componente sirve la ficha (lectura) y el formulario (edicion).
 * En edicion cada fila se escribe encima —tipo, nombre y fichero— sin botones
 * de editar y sin modales.
 */
export function PartAssetList({
  feature,
  editable,
  footer,
}: {
  feature: FeaturePublic
  editable?: boolean
  /** Se pinta al final de la lista: el selector de «anadir pieza». */
  footer?: ReactNode
}) {
  const rows = partRows(feature)
  const declaredIds = new Set((feature.parts ?? []).map((part) => part.id))

  if (rows.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">
          Todavia no hay ninguna pieza asociada a este feature.
        </p>
        {footer}
      </div>
    )
  }

  const assets = feature.assets ?? []
  const uploaded = assets.filter((asset) => asset.file).length
  const pieces = rows.filter((row) => row.part).length

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {pieces} pieza{pieces === 1 ? "" : "s"} · {assets.length} fichero
        {assets.length === 1 ? "" : "s"} · {uploaded} subido
        {uploaded === 1 ? "" : "s"}
      </p>
      {rows.map((row) => (
        <PartGroup
          key={row.part?.id ?? "sin-pieza"}
          feature={feature}
          row={row}
          declared={row.part ? declaredIds.has(row.part.id) : false}
          // Con una sola pieza, tenerla cerrada es un clic tonto.
          defaultOpen={rows.length === 1}
          editable={editable}
        />
      ))}
      {footer}
    </div>
  )
}
