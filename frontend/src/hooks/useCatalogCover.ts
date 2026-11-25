import { useQuery } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { ApiError, CatalogService } from "@/client"

/** A part and its features share one version check when their cards enter view. */
export function useCatalogCover(partId: string | null | undefined) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    if (!partId || !ref.current || visible) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true)
      },
      { rootMargin: "200px" },
    )
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [partId, visible])
  const query = useQuery({
    queryKey: ["features", "catalog", "cover", partId],
    queryFn: () => CatalogService.readPartCover({ partId: partId! }),
    enabled: Boolean(partId && visible),
    refetchOnWindowFocus: false,
    retry: (attempt, error) =>
      attempt < 2 &&
      (!(error instanceof ApiError) ||
        error.status === 429 ||
        error.status >= 500),
  })
  return {
    ref,
    cover: query.isSuccess && !query.isFetching ? query.data : undefined,
    error: query.error,
    retry: query.refetch,
    checking: query.isFetching,
  }
}
