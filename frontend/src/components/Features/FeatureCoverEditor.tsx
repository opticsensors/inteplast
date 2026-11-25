import { Box, ChevronLeft, ChevronRight, ImageIcon } from "lucide-react"
import { useEffect, useState } from "react"

import type { FeatureCover3D, FeatureDetail, FilePublic } from "@/client"
import { FeatureFaceWarning } from "@/components/Catalog/CatalogWarnings"
import { FileUpload } from "@/components/Common/FileUpload"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useFeaturePreview } from "@/hooks/useFeaturePreview"
import { CadCoverEditor } from "./CadCoverEditor"
import { CoverButton, RetryCoverButton } from "./CoverButton"
import { COVER_EDITOR_ROWS, CoverDialog } from "./CoverDialog"
import {
  type CoverDraft,
  type CoverSlide,
  coverPieceLabel,
} from "./coverSlides"
import { CarouselFrame, useCarousel } from "./FeatureCover"

interface CoverEditorProps {
  feature?: FeatureDetail
  /** One per piece, with the unsaved drafts already applied. */
  slides: CoverSlide[]
  /** Image of the feature itself, only used while it has no pieces. */
  image: FilePublic | null
  onImageChange: (image: FilePublic | null) => void
  onPartChange: (partId: string, draft: CoverDraft) => void
}

/**
 * The cover in edit mode: the same carousel as the page, with the pencil. It edits
 * the visible piece; «Aplicar» keeps a draft for it and the next piece can be edited
 * without closing. «Guardar» on the page saves them all
 * (docs/plan-portadas-por-pieza-2026-11-18.md, Interfaz).
 */
export function FeatureCoverEditor({
  feature,
  slides,
  image,
  onImageChange,
  onPartChange,
}: CoverEditorProps) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const { current, many, go } = useCarousel(slides.length)
  const slide = slides[current]
  const saved = feature?.part_covers?.find(
    (item) => item.part_id === slide?.part.id,
  )
  const sameCapture = Boolean(
    slide?.cover?.faces.length && saved?.image?.id === slide.image?.id,
  )
  const preview = useFeaturePreview({
    featureId: feature?.id,
    markedPartId:
      sameCapture && slide && feature?.marked_part_ids?.includes(slide.part.id)
        ? slide.part.id
        : undefined,
    original: slide?.image,
    immediate: true,
  })
  const name = feature?.name ?? "Portada del feature"

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) setOpen(next)
      }}
    >
      <div className="flex w-fit shrink-0 flex-col gap-2">
        {slide ? (
          <CarouselFrame
            code={coverPieceLabel(feature, slide)}
            current={current}
            count={slides.length}
            onStep={go}
          >
            <DialogTrigger asChild>
              <CoverButton
                editable
                image={preview.image}
                hasCover={Boolean(slide.image)}
                checking={preview.checking}
                name={`${name} · ${slide.part.code}`}
                className="size-full sm:size-full"
              />
            </DialogTrigger>
          </CarouselFrame>
        ) : (
          <DialogTrigger asChild>
            <CoverButton editable image={image} name={name} />
          </DialogTrigger>
        )}
        {preview.error && <RetryCoverButton onRetry={preview.retry} />}
        {feature && <FeatureFaceWarning feature={feature} />}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="px-1 text-xs has-[>svg]:px-1 sm:text-sm"
          onClick={() => setOpen(true)}
        >
          <ImageIcon className="size-4" />
          Cambiar imagen
        </Button>
      </div>
      {open && (
        <CoverDialog
          aria-describedby={undefined}
          showCloseButton={!busy}
          onPointerDownOutside={(event) => event.preventDefault()}
          onEscapeKeyDown={(event) => {
            if (busy) event.preventDefault()
          }}
        >
          <DialogHeader className="flex-row items-center gap-2 pr-8">
            <DialogTitle className="min-w-0 flex-1">Editar portada</DialogTitle>
            {slide && (
              <PieceStepper
                code={coverPieceLabel(feature, slide)}
                position={
                  many ? `${current + 1} / ${slides.length}` : undefined
                }
                disabled={busy}
                onStep={many ? go : undefined}
              />
            )}
          </DialogHeader>
          <CoverEditorDraft
            // A new piece starts a new draft: what was not applied is dropped.
            key={slide?.part.id ?? "feature"}
            feature={feature}
            partId={slide?.part.id}
            image={slide ? (slide.own ? slide.image : null) : image}
            previewImage={slide?.own ? (preview.image ?? null) : undefined}
            autoImage={
              feature?.part_covers?.find(
                (item) => item.part_id === slide?.part.id,
              )?.auto_image
            }
            cover={slide?.own ? slide.cover : null}
            setBusy={setBusy}
            close={() => setOpen(false)}
            onChange={(nextImage, cover) => {
              if (slide)
                onPartChange(slide.part.id, {
                  partCode: slide.part.code,
                  image: nextImage,
                  cover,
                })
              else onImageChange(nextImage)
              setBusy(false)
              // With more pieces the editor stays open to go on with the next one.
              if (!many) setOpen(false)
            }}
          />
        </CoverDialog>
      )}
    </Dialog>
  )
}

/** `‹ 3212 3 / 24 ›`: the piece being edited and how to move to another. */
function PieceStepper({
  code,
  position,
  disabled,
  onStep,
}: {
  code: string
  position?: string
  disabled: boolean
  onStep?: (delta: number) => void
}) {
  return (
    <div className="flex min-w-0 max-w-[72%] items-center gap-1 text-sm">
      {onStep && (
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="size-8"
          aria-label="Pieza anterior"
          title="Pieza anterior"
          disabled={disabled}
          onClick={() => onStep(-1)}
        >
          <ChevronLeft className="size-4" />
        </Button>
      )}
      <span className="flex min-w-0 items-center px-1">
        <span className="truncate font-mono" title={code}>
          {code}
        </span>
        {position && (
          <span className="ml-2 shrink-0 tabular-nums text-muted-foreground">
            {position}
          </span>
        )}
      </span>
      {onStep && (
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="size-8"
          aria-label="Pieza siguiente"
          title="Pieza siguiente"
          disabled={disabled}
          onClick={() => onStep(1)}
        >
          <ChevronRight className="size-4" />
        </Button>
      )}
    </div>
  )
}

/** Mount once per piece and opening: cancelling never changes the form's drafts. */
function CoverEditorDraft({
  feature,
  partId,
  image: initialImage,
  previewImage,
  autoImage,
  cover,
  onChange,
  setBusy,
  close,
}: {
  feature?: FeatureDetail
  /** The piece being edited; none while the feature has no pieces. */
  partId?: string
  image: FilePublic | null
  previewImage?: FilePublic | null
  autoImage?: FilePublic | null
  cover: FeatureCover3D | null
  onChange: (image: FilePublic | null, cover: FeatureCover3D | null) => void
  setBusy: (busy: boolean) => void
  close: () => void
}) {
  const [tab, setTab] = useState(cover ? "cad" : "image")
  const [cadVisited, setCadVisited] = useState(Boolean(cover))
  const [image, setImage] = useState(initialImage)
  const [imageChanged, setImageChanged] = useState(false)
  const [upload, setUpload] = useState({ pending: false, error: false })
  const [cadBusy, setCadBusy] = useState(false)
  const busy = upload.pending || cadBusy
  useEffect(() => setBusy(busy), [busy, setBusy])

  return (
    <Tabs
      className="gap-3"
      value={tab}
      onValueChange={(next) => {
        if (busy) return
        setTab(next)
        if (next === "cad") setCadVisited(true)
      }}
    >
      <TabsList aria-label="Origen de la portada">
        <TabsTrigger value="image" disabled={busy}>
          <ImageIcon />
          Imagen
        </TabsTrigger>
        <TabsTrigger value="cad" disabled={busy}>
          <Box />
          CAD
        </TabsTrigger>
      </TabsList>
      <TabsContent value="image" className={COVER_EDITOR_ROWS}>
        <FileUpload
          value={image}
          previewOverride={imageChanged ? undefined : previewImage}
          previewFallback={autoImage}
          variant="image"
          pasteInDialog
          coverLayout
          boxClassName="size-full"
          onUploadStateChange={setUpload}
          onChange={(file) => {
            setImage(file)
            setImageChanged(true)
          }}
        />
        <DialogFooter className="flex-row justify-end">
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={close}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            disabled={busy || upload.error || !imageChanged}
            onClick={() => {
              onChange(image, null)
              setImageChanged(false)
            }}
          >
            {image ? "Aplicar" : "Quitar portada"}
          </Button>
        </DialogFooter>
      </TabsContent>
      {cadVisited && (
        <TabsContent value="cad" forceMount hidden={tab !== "cad"}>
          <CadCoverEditor
            feature={feature}
            partId={partId}
            initial={cover}
            image={previewImage === undefined ? initialImage : previewImage}
            autoImage={autoImage}
            setBusy={setCadBusy}
            onSaved={onChange}
            close={close}
          />
        </TabsContent>
      )}
    </Tabs>
  )
}
