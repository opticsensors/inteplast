import { ChevronLeft, ChevronRight } from "lucide-react"
import {
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
  Suspense,
  type TouchEvent,
  useMemo,
  useRef,
  useState,
} from "react"

import type { FeatureCover3D, FeatureDetail, FilePublic } from "@/client"
import { FeatureFaceWarning } from "@/components/Catalog/CatalogWarnings"
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useFeaturePreview } from "@/hooks/useFeaturePreview"
import { usePrepareCover } from "@/hooks/usePrepareCover"
import { cn } from "@/lib/utils"
import { COVER_SIZE, CoverButton, RetryCoverButton } from "./CoverButton"
import { CoverDialog } from "./CoverDialog"
import { CoverLoading } from "./CoverLoading"
import { coverAsset } from "./cadCover"
import { coverPieceLabel, coverSlides, step } from "./coverSlides"
import { FeatureThumbnail } from "./FeatureCard"
import { preloadStepViewer, StepCoverCanvas } from "./lazyStepCoverCanvas"

/** Minimum horizontal travel, in px, for a finger swipe to change piece. */
const SWIPE = 40
/** A click this soon (ms) after a swipe is the end of the gesture, not a tap. */
const SWIPE_CLICK = 400

const chip =
  "pointer-events-none absolute top-2 z-10 rounded-md border bg-background/95 px-1.5 py-0.5 text-xs shadow-sm"

/** What one view of the cover shows: a piece's capture, or the feature image. */
interface CoverView {
  image: FilePublic | null
  cover: FeatureCover3D | null
  code?: string
}

/** Index of the visible piece, kept inside the list when pieces come and go. */
export function useCarousel(count: number) {
  const [index, setIndex] = useState(0)
  const current = Math.min(index, Math.max(count - 1, 0))
  return {
    current,
    many: count > 1,
    go: (delta: number) => setIndex(step(current, delta, count)),
  }
}

/** ← / → change piece; used by the page, the viewer and the editor. */
export const arrowStep =
  (onStep: ((delta: number) => void) | undefined) => (event: KeyboardEvent) => {
    if (!onStep || (event.key !== "ArrowLeft" && event.key !== "ArrowRight"))
      return
    event.preventDefault()
    onStep(event.key === "ArrowLeft" ? -1 : 1)
  }

/**
 * A horizontal finger swipe changes piece. Without `onStep` it does nothing, so a 3D view
 * keeps the gesture to rotate the part.
 */
function useSwipe(onStep: ((delta: number) => void) | undefined) {
  const touch = useRef<number | null>(null)
  // When the last swipe ended: only a click right after it belongs to the gesture.
  const swiped = useRef(0)
  if (!onStep) return {}
  return {
    onTouchStart: (event: TouchEvent) => {
      touch.current = event.touches[0]?.clientX ?? null
    },
    onTouchEnd: (event: TouchEvent) => {
      const start = touch.current
      const end = event.changedTouches[0]?.clientX
      touch.current = null
      if (start === null || end === undefined) return
      if (Math.abs(end - start) < SWIPE) return
      swiped.current = Date.now()
      onStep(end < start ? 1 : -1)
    },
    onClickCapture: (event: MouseEvent) => {
      // A swipe may end with a click on the capture: it must not open anything.
      if (Date.now() - swiped.current > SWIPE_CLICK) return
      swiped.current = 0
      event.preventDefault()
      event.stopPropagation()
    },
  }
}

/**
 * The capture with what tells the pieces apart: the code on the left and, with two
 * pieces or more, the position on the right and arrows on both sides. Keyboard and
 * finger swipe change piece; nothing goes below the capture.
 */
export function CarouselFrame({
  code,
  current,
  count,
  onStep,
  children,
}: {
  code?: string
  current: number
  count: number
  onStep: (delta: number) => void
  /** The capture button. */
  children: ReactNode
}) {
  const many = count > 1
  const swipe = useSwipe(many ? onStep : undefined)
  return (
    <section
      aria-label={many ? "Capturas de las piezas" : "Captura de la pieza"}
      className={cn("group/cover relative shrink-0", COVER_SIZE)}
      onKeyDown={arrowStep(many ? onStep : undefined)}
      {...swipe}
    >
      {children}
      {code && (
        <span
          title={code}
          className={cn(chip, "left-2 max-w-[70%] truncate font-mono")}
        >
          {code}
        </span>
      )}
      {many && (
        <>
          <span className={cn(chip, "right-2 tabular-nums")}>
            {current + 1} / {count}
          </span>
          <span className="sr-only" aria-live="polite">
            Pieza {current + 1} de {count}: {code}
          </span>
          <ArrowButton side="left" onClick={() => onStep(-1)} hover />
          <ArrowButton side="right" onClick={() => onStep(1)} hover />
        </>
      )}
    </section>
  )
}

/**
 * Cover of the feature page: one capture per piece (decisions 1 and 5 of
 * docs/plan-portadas-por-pieza-2026-11-18.md). With one piece, only its code; with
 * more, the position and arrows too. Without pieces, the feature image as before.
 */
export function FeatureCover({ feature }: { feature: FeatureDetail }) {
  const slides = useMemo(() => coverSlides(feature), [feature])
  const [expanded, setExpanded] = useState(false)
  const { current, many, go } = useCarousel(slides.length)
  const slide = slides[current]
  const preview = useFeaturePreview({
    featureId: feature.id,
    markedPartId:
      slide && feature.marked_part_ids?.includes(slide.part.id)
        ? slide.part.id
        : undefined,
    original: slide?.image,
    immediate: true,
  })
  const view: CoverView = slide
    ? {
        image: preview.image ?? null,
        cover: preview.review ? null : slide.cover,
        code: coverPieceLabel(feature, slide),
      }
    : { image: feature.image ?? null, cover: null }
  usePrepareCover(
    view.cover ? coverAsset(feature, view.cover)?.file : null,
    view.cover?.source_sha256,
  )

  if (!slide && !feature.image)
    return <FeatureThumbnail feature={feature} className={COVER_SIZE} />

  return (
    <Dialog open={expanded} onOpenChange={setExpanded}>
      <div className="flex w-fit shrink-0 flex-col">
        <CarouselFrame
          code={view.code}
          current={current}
          count={slides.length}
          onStep={go}
        >
          {view.image || view.cover ? (
            <DialogTrigger asChild>
              <CoverButton
                image={view.image}
                checking={preview.checking}
                onPointerEnter={view.cover ? preloadStepViewer : undefined}
                onFocus={view.cover ? preloadStepViewer : undefined}
                name={
                  view.code ? `${feature.name} · ${view.code}` : feature.name
                }
                className="size-full sm:size-full"
              />
            </DialogTrigger>
          ) : (
            // A piece without any capture shows the image icon, with nothing to enlarge;
            // never the feature's own image, which is only for features without pieces.
            <FeatureThumbnail
              feature={{ image: null, name: feature.name }}
              className="size-full"
            />
          )}
        </CarouselFrame>
        {preview.error && <RetryCoverButton onRetry={preview.retry} />}
        <FeatureFaceWarning feature={feature} />
      </div>
      {expanded && (
        <CoverViewer
          feature={feature}
          view={view}
          position={many ? `${current + 1} / ${slides.length}` : undefined}
          onStep={many ? go : undefined}
        />
      )}
    </Dialog>
  )
}

export function ArrowButton({
  side,
  onClick,
  hover = false,
}: {
  side: "left" | "right"
  onClick: () => void
  /** On the page they appear with the pointer or focus; always on touch screens. */
  hover?: boolean
}) {
  const Icon = side === "left" ? ChevronLeft : ChevronRight
  const label = side === "left" ? "Pieza anterior" : "Pieza siguiente"
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={cn(
        "absolute top-1/2 z-10 flex size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-md border bg-background/95 text-foreground shadow-sm transition-opacity hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        side === "left" ? "left-2" : "right-2",
        hover &&
          "opacity-0 group-hover/cover:opacity-100 group-focus-within/cover:opacity-100 [@media(hover:none)]:opacity-100",
      )}
    >
      <Icon className="size-4" />
    </button>
  )
}

function CoverViewer({
  feature,
  view,
  position,
  onStep,
}: {
  feature: FeatureDetail
  view: CoverView
  position?: string
  onStep?: (delta: number) => void
}) {
  const cover = view.cover
  const asset = cover ? coverAsset(feature, cover) : undefined
  // Swipe only over a still image: on the 3D view the finger rotates the part.
  const swipe = useSwipe(cover && asset?.file ? undefined : onStep)
  const image = (
    <FeatureThumbnail
      feature={{ image: view.image, name: feature.name }}
      fit="contain"
      className="size-full"
    />
  )
  let content: ReactNode = image
  if (cover)
    content = asset?.file ? (
      <Suspense
        fallback={
          <>
            {image}
            <CoverLoading />
          </>
        }
      >
        {/* Only the visible piece loads its STEP; changing piece unmounts it and
            cancels its worker, as closing does. */}
        <StepCoverCanvas
          key={asset.id}
          file={asset.file}
          initial={cover}
          color={feature.color}
          fallback={image}
          className="size-full"
        />
      </Suspense>
    ) : (
      <div className="relative size-full">
        {image}
        <p
          role="alert"
          className="absolute inset-x-2 bottom-2 rounded bg-background/95 p-3 text-sm"
        >
          El CAD vinculado ha cambiado o ya no está disponible. Revisa la
          portada desde Editar.
        </p>
      </div>
    )

  return (
    <CoverDialog onKeyDown={arrowStep(onStep)}>
      <DialogHeader>
        <DialogTitle className="pr-6">{feature.name}</DialogTitle>
        <DialogDescription className="sr-only">
          {cover ? "Portada 3D de la pieza." : "Imagen de portada ampliada."}
        </DialogDescription>
      </DialogHeader>
      <div
        data-slot="cover-surface"
        className="relative size-[var(--cover-size)]"
        {...swipe}
      >
        <div key={view.code ?? "feature"} className="size-full">
          {content}
        </div>
        {/* Top right belongs to the 3D tools: code and position go together on the left. */}
        {view.code && (
          <span className={cn(chip, "left-2 flex max-w-[72%] items-center")}>
            <span className="truncate font-mono" title={view.code}>
              {view.code}
            </span>
            {position && (
              <span className="ml-2 shrink-0 tabular-nums text-muted-foreground">
                {position}
              </span>
            )}
          </span>
        )}
        {onStep && (
          <>
            <ArrowButton side="left" onClick={() => onStep(-1)} />
            <ArrowButton side="right" onClick={() => onStep(1)} />
          </>
        )}
      </div>
    </CoverDialog>
  )
}
