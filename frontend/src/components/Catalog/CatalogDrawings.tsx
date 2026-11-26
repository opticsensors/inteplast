import { useInfiniteQuery, useQuery } from "@tanstack/react-query"
import { FileText, Loader2, Search } from "lucide-react"
import { useState } from "react"

import {
  CatalogService,
  type DrawingCard,
  EvidenceService,
  FilesService,
} from "@/client"
import { partLabel } from "@/components/Features/parts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDrawingThumbnail } from "@/hooks/useDrawingThumbnail"
import { absoluteFileUrl, fileErrorMessage } from "@/hooks/useFileAccess"

export type CatalogDrawingsRequest = {
  q: string
  partId: string | null
  featureId: string | null
  familyId: string | null
  customerId: string | null
  materialId: string | null
}

const PAGE = 40
const BUSY_RETRY_MS = 3000

/**
 * First page of the PDF, drawn by the server once per version of the original. While it
 * is being drawn, or others are, a placeholder stays and the request is repeated.
 */
function DrawingThumbnail({ card }: { card: DrawingCard }) {
  // An expired or unreachable image shows the drawing icon, never a broken image.
  const [broken, setBroken] = useState(false)
  const thumbnail = useDrawingThumbnail(card.file)
  if (thumbnail.data?.url && !broken)
    return (
      <img
        src={absoluteFileUrl(thumbnail.data.url)}
        alt={`Primera página de ${card.name}`}
        className="size-full object-contain"
        onError={() => setBroken(true)}
      />
    )
  return (
    <div
      className="flex size-full items-center justify-center text-muted-foreground"
      title={thumbnail.error ? fileErrorMessage(thumbnail.error) : undefined}
    >
      {broken || thumbnail.isError ? (
        <FileText className="size-10" aria-label="Sin miniatura" />
      ) : (
        <Loader2
          className="size-6 animate-spin"
          aria-label="Preparando miniatura"
        />
      )}
    </div>
  )
}

const markLabels = {
  pending: "Leyendo plano…",
  unavailable: "Lectura no disponible",
  balloons: "Globos detectados",
  numbered: "Numeración detectada",
  icp_marks: "Marcas del archivo .icp",
  inconclusive: "Marcas sin identificar",
  none: "Sin marcas detectadas",
}

function DrawingMarkBadge({ card }: { card: DrawingCard }) {
  const check = useQuery({
    queryKey: ["drawing-icp-check", card.file.id, card.file.version],
    queryFn: () => FilesService.checkDrawingIcp({ fileId: card.file.id }),
    // The server knows the current .icp of the drawing, the browser does not: ask again
    // each time Planos opens, never showing a remembered label meanwhile.
    staleTime: 0,
    gcTime: 0,
    // Queued behind other checks: keep asking while the page is open, without a limit
    // shorter than the server's own time per check.
    refetchInterval: (query) =>
      query.state.data?.state === "busy" ? BUSY_RETRY_MS : false,
    refetchIntervalInBackground: true,
  })
  const verified =
    check.isSuccess && check.data.state === "ready" && check.data.verified
  const readMarks =
    check.isError || (check.data?.state === "ready" && !verified)
  const marks = useQuery({
    queryKey: ["drawing-marks", card.file.id, card.file.version],
    queryFn: () =>
      EvidenceService.prepareDrawingMarks({ fileId: card.file.id }),
    enabled: readMarks,
    staleTime: 0,
    gcTime: 0,
    refetchInterval: (query) =>
      query.state.data === "pending" ? BUSY_RETRY_MS : false,
  })
  const status = marks.isError ? "unavailable" : (marks.data ?? "pending")
  const label = verified
    ? "Globos verificados con .icp"
    : markLabels[readMarks ? status : "pending"]
  return (
    <Badge
      variant="outline"
      className={`max-w-full truncate font-normal ${verified ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-300" : "text-muted-foreground"}`}
    >
      {label}
    </Badge>
  )
}

function DrawingTile({
  card,
  onOpen,
}: {
  card: DrawingCard
  onOpen: (card: DrawingCard) => void
}) {
  const label = `${card.name} · ${card.part.code}`
  return (
    <div className="relative flex min-w-0 flex-col overflow-hidden rounded-lg border border-t-4 border-t-amber-500/60 transition-colors hover:border-primary/50 hover:bg-accent/50">
      <button
        type="button"
        className="absolute inset-0 z-10 cursor-pointer rounded-lg"
        onClick={() => onOpen(card)}
        title={label}
      >
        <span className="sr-only">Abrir plano {label}</span>
      </button>
      <div className="aspect-[4/3] w-full bg-white p-2">
        <DrawingThumbnail card={card} />
      </div>
      <div className="min-w-0 space-y-0.5 p-3">
        <h3 className="truncate font-semibold leading-tight" title={card.name}>
          {card.name}
        </h3>
        <p className="truncate text-sm text-muted-foreground">
          {partLabel(card.part)}
        </p>
        <DrawingMarkBadge card={card} />
        {(card.component || card.revision) && (
          <p className="truncate text-sm text-muted-foreground">
            {[card.component, card.revision && `rev. ${card.revision}`]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
      </div>
    </div>
  )
}

/** «Planos»: every drawing of the loaded pieces, always as a grid. */
export function CatalogDrawings({
  request,
  onOpen,
}: {
  request: CatalogDrawingsRequest
  onOpen: (card: DrawingCard) => void
}) {
  const result = useInfiniteQuery({
    queryKey: ["features", "catalog-drawings", request],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      CatalogService.readCatalogDrawings({
        q: request.q,
        partId: request.partId,
        featureId: request.featureId,
        familyId: request.familyId,
        customerId: request.customerId,
        materialId: request.materialId,
        skip: pageParam,
        limit: PAGE,
      }),
    getNextPageParam: (last, pages) =>
      pages.length * PAGE < last.count ? pages.length * PAGE : undefined,
  })
  if (result.isPending)
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {[0, 1, 2, 3].map((index) => (
          <Skeleton key={index} className="aspect-[4/3] w-full" />
        ))}
      </div>
    )
  if (result.error) return <p role="alert">{fileErrorMessage(result.error)}</p>
  const cards = (result.data?.pages ?? []).flatMap((page) => page.data)
  return (
    <div className="space-y-4">
      {cards.length ? (
        <div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
          data-view="drawings"
        >
          {cards.map((card) => (
            <DrawingTile
              key={`${card.part.id}-${card.file.id}`}
              card={card}
              onOpen={onOpen}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <Search className="size-8 text-muted-foreground" />
          <p className="text-lg font-semibold">No hay planos</p>
        </div>
      )}
      {result.hasNextPage && (
        <Button
          variant="outline"
          disabled={result.isFetchingNextPage}
          onClick={() => void result.fetchNextPage()}
        >
          {result.isFetchingNextPage ? "Cargando…" : "Mostrar más"}
        </Button>
      )}
    </div>
  )
}
