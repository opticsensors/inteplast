import type {
  FeatureAssetPublic,
  FeatureCover3D,
  FeaturePublic,
} from "@/client"

export const COVER_RECIPE = "occt-import-js@0.0.23/cover-v1" as const
export const MAX_COVER_STEP_SIZE = 50 * 1024 * 1024

export const isPartStep = (asset: FeatureAssetPublic) =>
  asset.kind === "part" &&
  Boolean(
    asset.part && asset.file && /\.(step|stp)$/i.test(asset.file.filename),
  )

export const coverAssets = (feature?: FeaturePublic) =>
  (feature?.assets ?? []).filter(isPartStep)

export function coverAsset(feature: FeaturePublic, cover: FeatureCover3D) {
  return coverAssets(feature).find(
    (asset) =>
      asset.id === cover.asset_id &&
      asset.part?.id === cover.part_id &&
      asset.file?.id === cover.file_id &&
      (asset.file?.version ?? null) === (cover.file_version ?? null),
  )
}

export const sha256 = async (bytes: ArrayBuffer) =>
  Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")

export type CoverCapture = {
  image: Blob
  annotation: Pick<
    FeatureCover3D,
    "source_sha256" | "geometry_key" | "recipe" | "faces" | "camera"
  >
}

export type CoverControls = {
  capture: () => Promise<CoverCapture>
  clear: () => void
}
