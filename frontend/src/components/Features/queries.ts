import {
  type FeaturesReadFeaturesData,
  FeaturesService,
  PartsService,
} from "@/client"

/**
 * Claves de cache. Todo cuelga de ["features"], asi que invalidar esa raiz
 * refresca a la vez el catalogo y las fichas.
 * Las piezas van aparte: se comparten entre features y cambian mucho menos.
 */
export const featuresQueryOptions = (
  params: FeaturesReadFeaturesData = {},
) => ({
  queryKey: ["features", params] as const,
  queryFn: () => FeaturesService.readFeatures(params),
})

export const featureQueryOptions = (featureId: string) => ({
  queryKey: ["features", "detail", featureId] as const,
  queryFn: () => FeaturesService.readFeature({ featureId }),
})

export const featureFiltersQueryOptions = () => ({
  queryKey: ["features", "filters"] as const,
  queryFn: () => FeaturesService.readFeatureFilters(),
})

export const partsQueryOptions = () => ({
  queryKey: ["parts"] as const,
  queryFn: async () => {
    const result = await PartsService.readParts({ limit: 100 })
    while (result.data.length < result.count) {
      const next = await PartsService.readParts({
        skip: result.data.length,
        limit: 100,
      })
      if (!next.data.length) break
      result.data.push(...next.data)
      result.count = next.count
    }
    return result
  },
})
