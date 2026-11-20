import type {
  FeatureCover3D,
  FeatureDetail,
  FilePublic,
  PartPublic,
} from "@/client"
import { coverAssets } from "./cadCover"
import { featureParts } from "./parts"

/** What the cover shows for one piece of the feature. */
export interface CoverSlide {
  part: PartPublic
  /** The capture made for this feature, else the piece's CAD capture, else none. */
  image: FilePublic | null
  /** Faces and camera, only when the shown image is this feature's own CAD cover. */
  cover: FeatureCover3D | null
  /** True when the image is the feature's own capture on this piece. */
  own: boolean
}

export function coverPieceLabel(
  feature: FeatureDetail | undefined,
  slide: CoverSlide,
) {
  const files = coverAssets(feature).filter(
    (asset) => asset.part?.id === slide.part.id,
  )
  const selected = files.find((asset) => asset.id === slide.cover?.asset_id)
  return files.length > 1 && selected
    ? `${slide.part.code} · ${selected.name}`
    : slide.part.code
}

/**
 * One slide per piece, in the order the server gives in `part_covers`: the first one is
 * the cover of the card (docs/plan-portadas-por-pieza-2026-11-18.md, decision 4), so the
 * card and the page never disagree. A piece the server has not listed yet goes last.
 */
export function coverSlides(feature: FeatureDetail): CoverSlide[] {
  const covers = new Map(
    (feature.part_covers ?? []).map((cover) => [cover.part_id, cover]),
  )
  const parts = new Map(featureParts(feature).map((part) => [part.id, part]))
  const ordered = [
    ...(feature.part_covers ?? []).flatMap((cover) => {
      const part = parts.get(cover.part_id)
      return part ? [part] : []
    }),
    ...[...parts.values()].filter((part) => !covers.has(part.id)),
  ]
  return ordered.map((part) => {
    const cover = covers.get(part.id)
    const own = cover?.image ?? null
    return {
      part,
      image: own ?? cover?.auto_image ?? null,
      cover: own ? (cover?.cover_3d ?? null) : null,
      own: Boolean(own),
    }
  })
}

/** A cover edited on one piece and not saved yet; no image = back to the CAD one. */
export interface CoverDraft {
  partCode: string
  image: FilePublic | null
  cover: FeatureCover3D | null
}

/** The slides as the editor shows them: unsaved drafts over the saved covers. */
export function withDrafts(
  feature: FeatureDetail,
  drafts: ReadonlyMap<string, CoverDraft>,
): CoverSlide[] {
  const auto = new Map(
    (feature.part_covers ?? []).map((cover) => [
      cover.part_id,
      cover.auto_image ?? null,
    ]),
  )
  return coverSlides(feature).map((slide) => {
    const draft = drafts.get(slide.part.id)
    if (!draft) return slide
    return {
      ...slide,
      image: draft.image ?? auto.get(slide.part.id) ?? null,
      cover: draft.image ? draft.cover : null,
      own: Boolean(draft.image),
    }
  })
}

/** Next index, wrapping around at both ends. */
export const step = (index: number, delta: number, count: number) =>
  count ? (((index + delta) % count) + count) % count : 0
