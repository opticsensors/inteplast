import type {
  AssetKind,
  FeatureAssetPublic,
  FeaturePublic,
  PartPublic,
} from "@/client"

import { ASSET_KINDS } from "./constants"

/** Una fila de la matriz: la pieza y sus ficheros repartidos por tipo. */
export interface PartRow {
  /** null = adjuntos que se quedaron sin pieza (se borro la pieza). */
  part: PartPublic | null
  assets: Record<AssetKind, FeatureAssetPublic[]>
  total: number
}

/** Por codigo, comparando numeros como numeros: 3051 antes que 3212. */
const byCode = (a: PartPublic, b: PartPublic) =>
  a.code.localeCompare(b.code, undefined, { numeric: true })

/**
 * Las piezas del feature: las declaradas explicitamente (`parts`) mas las que
 * aportan algun fichero (`assets[].part`). Son dos caminos al mismo sitio y el
 * usuario espera verlas juntas, sin duplicados.
 */
export function featureParts(feature: FeaturePublic): PartPublic[] {
  const byId = new Map<string, PartPublic>()
  for (const part of feature.parts ?? []) byId.set(part.id, part)
  for (const asset of feature.assets ?? []) {
    if (asset.part) byId.set(asset.part.id, asset.part)
  }
  return [...byId.values()].sort(byCode)
}

const emptyAssets = (): Record<AssetKind, FeatureAssetPublic[]> => {
  const cells = {} as Record<AssetKind, FeatureAssetPublic[]>
  for (const kind of ASSET_KINDS) cells[kind] = []
  return cells
}

/**
 * Las filas de la matriz. Una pieza declarada sin ficheros sale igual, con la
 * fila entera vacia: es justo lo que hace visible lo que falta por subir.
 */
export function partRows(feature: FeaturePublic): PartRow[] {
  const rows = new Map<string, PartRow>()
  for (const part of featureParts(feature)) {
    rows.set(part.id, { part, assets: emptyAssets(), total: 0 })
  }

  const orphans: PartRow = { part: null, assets: emptyAssets(), total: 0 }
  for (const asset of feature.assets ?? []) {
    const row = asset.part ? rows.get(asset.part.id) : orphans
    if (!row) continue
    row.assets[asset.kind].push(asset)
    row.total += 1
  }

  const result = [...rows.values()]
  if (orphans.total > 0) result.push(orphans)
  return result
}

/** "3212 - Pump Housing", o solo el codigo si la pieza no tiene nombre. */
export const partLabel = (part: PartPublic) =>
  part.name ? `${part.code} - ${part.name}` : part.code
