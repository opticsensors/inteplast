import { Box, FileText, Package, ScanLine, Waves } from "lucide-react"

import type { AssetKind, FeatureCategory, NoteKind } from "@/client"

/** Tipos geometricos comunes con los que se clasifica un feature. */
export const CATEGORY_LABELS: Record<FeatureCategory, string> = {
  hole: "Agujero",
  rib: "Nervio",
  thickness: "Espesor",
  boss: "Boss",
  fillet: "Radio",
  draft: "Angulo de desmoldeo",
  other: "Otro",
}

export const CATEGORIES = Object.keys(CATEGORY_LABELS) as FeatureCategory[]

/**
 * Los cinco ficheros que puede aportar una pieza. El orden es el de las filas
 * dentro de cada pieza: primero el molde y la pieza, luego los documentos.
 */
export const ASSET_KIND_LABELS: Record<AssetKind, string> = {
  mold: "Molde",
  part: "Pieza CAD",
  scan: "Pieza escaneada",
  drawing: "Plano 2D",
  moldflow: "Moldflow",
}

/** Etiqueta de la fila en la lista de ficheros: va en una columna estrecha. */
export const ASSET_KIND_SHORT: Record<AssetKind, string> = {
  mold: "Molde",
  part: "CAD",
  scan: "Escaneo",
  drawing: "Plano",
  moldflow: "Moldflow",
}

export const ASSET_KIND_SINGULAR: Record<AssetKind, string> = {
  mold: "molde",
  part: "pieza CAD",
  scan: "pieza escaneada",
  drawing: "plano 2D",
  moldflow: "estudio Moldflow",
}

export const ASSET_KINDS = Object.keys(ASSET_KIND_LABELS) as AssetKind[]

export const ASSET_ICONS: Record<AssetKind, typeof Box> = {
  mold: Box,
  part: Package,
  scan: ScanLine,
  drawing: FileText,
  moldflow: Waves,
}

export const NOTE_KIND_LABELS: Record<NoteKind, string> = {
  warning: "Warnings",
  lesson: "Lessons Learned",
}

export const NOTE_KIND_SINGULAR: Record<NoteKind, string> = {
  warning: "advertencia",
  lesson: "leccion aprendida",
}
