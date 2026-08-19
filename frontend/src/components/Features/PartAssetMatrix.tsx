import { Download, FileQuestion } from "lucide-react"

import type { AssetKind, FeatureAssetPublic, FeaturePublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { fileUrl } from "@/utils"
import {
  ASSET_ICONS,
  ASSET_KIND_LABELS,
  ASSET_KIND_SHORT,
  ASSET_KINDS,
} from "./constants"
import { type PartRow, partRows } from "./parts"

/** Una casilla: los ficheros de esa pieza y de ese tipo, casi siempre uno. */
function AssetCell({
  kind,
  assets,
}: {
  kind: AssetKind
  assets: FeatureAssetPublic[]
}) {
  if (assets.length === 0) {
    return (
      <span className="text-muted-foreground/50" title="No hay">
        -
      </span>
    )
  }

  const Icon = ASSET_ICONS[kind]

  return (
    <div className="flex flex-col items-center gap-1">
      {assets.map((asset) =>
        asset.file ? (
          <Button
            key={asset.id}
            variant="ghost"
            size="icon"
            className="size-7"
            title={`Descargar ${asset.name}`}
            asChild
          >
            <a
              href={fileUrl(asset.file.id)}
              download={asset.file.filename}
              target="_blank"
              rel="noreferrer"
            >
              <Download className="size-4" />
              <span className="sr-only">Descargar {asset.name}</span>
            </a>
          </Button>
        ) : (
          // Declarado pero sin subir: por eso la matriz vale de checklist
          <span
            key={asset.id}
            className="flex size-7 items-center justify-center text-muted-foreground"
            title={`${asset.name} (sin fichero subido)`}
          >
            <Icon className="size-4 opacity-40" />
          </span>
        ),
      )}
    </div>
  )
}

function PartCell({ row }: { row: PartRow }) {
  if (!row.part) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <FileQuestion className="size-4 shrink-0" />
        <span className="text-sm">Sin pieza</span>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-baseline gap-x-2">
      <span className="font-mono font-semibold">{row.part.code}</span>
      {row.part.name && (
        <span className="text-sm text-muted-foreground">{row.part.name}</span>
      )}
    </div>
  )
}

/**
 * Las piezas del feature, una por fila, con una columna por tipo de fichero.
 *
 * Se agrupa por pieza y no por tipo porque lo que el usuario quiere saber es
 * "en cuantas piezas aparece esto y que tengo de cada una". Con las filas
 * vacias a la vista, tambien enseña lo que falta por subir.
 */
export function PartAssetMatrix({ feature }: { feature: FeaturePublic }) {
  const rows = partRows(feature)

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Todavia no hay ninguna pieza asociada a este feature.
      </p>
    )
  }

  const files = (feature.assets ?? []).length
  const pieces = rows.filter((row) => row.part).length

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {pieces} pieza{pieces === 1 ? "" : "s"} · {files} fichero
        {files === 1 ? "" : "s"}
      </p>
      {/* La tabla tiene 6 columnas: en movil se desplaza en horizontal */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-40">Pieza</TableHead>
              {ASSET_KINDS.map((kind) => (
                <TableHead
                  key={kind}
                  className="text-center"
                  title={ASSET_KIND_LABELS[kind]}
                >
                  {ASSET_KIND_SHORT[kind]}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.part?.id ?? "sin-pieza"}>
                <TableCell>
                  <PartCell row={row} />
                </TableCell>
                {ASSET_KINDS.map((kind) => (
                  <TableCell key={kind} className="text-center">
                    <AssetCell kind={kind} assets={row.assets[kind]} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
