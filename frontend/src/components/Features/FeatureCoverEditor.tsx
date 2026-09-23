import { Box, ImageIcon } from "lucide-react"
import { useEffect, useState } from "react"

import type { FeatureCover3D, FeaturePublic, FilePublic } from "@/client"
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
import { CadCoverEditor } from "./CadCoverEditor"
import { CoverButton } from "./CoverButton"
import { COVER_EDITOR_ROWS, CoverDialog } from "./CoverDialog"

interface CoverEditorProps {
  feature?: FeaturePublic
  image: FilePublic | null
  cover: FeatureCover3D | null
  onChange: (image: FilePublic | null, cover: FeatureCover3D | null) => void
}

export function FeatureCoverEditor(props: CoverEditorProps) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) setOpen(next)
      }}
    >
      <div className="flex w-32 shrink-0 flex-col gap-2 sm:w-48">
        <DialogTrigger asChild>
          <CoverButton
            editable
            image={props.image}
            name={props.feature?.name ?? "Portada del feature"}
          />
        </DialogTrigger>
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
          <DialogHeader>
            <DialogTitle>Editar portada</DialogTitle>
          </DialogHeader>
          <CoverEditorDraft
            {...props}
            setBusy={setBusy}
            close={() => setOpen(false)}
            onChange={(image, cover) => {
              props.onChange(image, cover)
              setBusy(false)
              setOpen(false)
            }}
          />
        </CoverDialog>
      )}
    </Dialog>
  )
}

/** Mount once per opening: cancelling never changes the form's cover draft. */
function CoverEditorDraft({
  feature,
  image: initialImage,
  cover,
  onChange,
  setBusy,
  close,
}: CoverEditorProps & { setBusy: (busy: boolean) => void; close: () => void }) {
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
            onClick={() => onChange(image, null)}
          >
            {image ? "Aplicar" : "Quitar portada"}
          </Button>
        </DialogFooter>
      </TabsContent>
      {cadVisited && (
        <TabsContent value="cad" forceMount hidden={tab !== "cad"}>
          <CadCoverEditor
            feature={feature}
            initial={cover}
            image={initialImage}
            setBusy={setCadBusy}
            onSaved={onChange}
            close={close}
          />
        </TabsContent>
      )}
    </Tabs>
  )
}
