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

/** Los tres grupos de la seccion "Piezas ejemplo". */
export const ASSET_KIND_LABELS: Record<AssetKind, string> = {
  mold: "Moldes",
  part: "Pieza ref.",
  drawing: "Plano 2D",
}

export const ASSET_KIND_SINGULAR: Record<AssetKind, string> = {
  mold: "molde",
  part: "pieza ref.",
  drawing: "plano 2D",
}

export const ASSET_KINDS = Object.keys(ASSET_KIND_LABELS) as AssetKind[]

export const NOTE_KIND_LABELS: Record<NoteKind, string> = {
  warning: "Warnings",
  lesson: "Lessons Learned",
}

export const NOTE_KIND_SINGULAR: Record<NoteKind, string> = {
  warning: "advertencia",
  lesson: "leccion aprendida",
}
