import { Box, FileText, Package, ScanLine, Waves } from "lucide-react"

import type { AssetKind, NoteKind } from "@/client"

export const MAX_HEADER_NAME_LENGTH = 45
export const MAX_HEADER_DESCRIPTION_LENGTH = 200

/**
 * Los cinco ficheros que puede aportar una pieza. El orden es el de las filas
 * dentro de cada pieza: primero el molde y la pieza, luego los documentos.
 */
export const ASSET_KIND_LABELS: Record<AssetKind, string> = {
  mold: "CAD molde",
  part: "CAD pieza",
  scan: "Escaneo",
  drawing: "Plano 2D",
  moldflow: "Moldflow",
}

export const ASSET_KINDS = Object.keys(ASSET_KIND_LABELS) as AssetKind[]

export const ASSET_ICONS: Record<AssetKind, typeof Box> = {
  mold: Box,
  part: Package,
  scan: ScanLine,
  drawing: FileText,
  moldflow: Waves,
}

export const NOTE_KIND_SINGULAR: Record<NoteKind, string> = {
  warning: "advertencia",
  lesson: "lección aprendida",
}
