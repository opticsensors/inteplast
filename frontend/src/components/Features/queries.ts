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
  queryFn: () => PartsService.readParts(),
})
