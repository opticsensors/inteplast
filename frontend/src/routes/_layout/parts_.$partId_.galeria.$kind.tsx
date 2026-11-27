import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { CatalogService } from "@/client"
import { partLabel } from "@/components/Features/parts"
import { isFolderAttachment } from "@/components/Parts/AttachmentActions"
import { AttachmentDetail } from "@/components/Parts/AttachmentGallery"
import { savedFiles } from "@/components/Parts/pieceFileDrafts"
import { fileErrorMessage } from "@/hooks/useFileAccess"

export const Route = createFileRoute("/_layout/parts_/$partId_/galeria/$kind")({
  component: GalleryPage,
})

function GalleryPage() {
  const { partId, kind } = Route.useParams()
  const part = useQuery({
    queryKey: ["parts", "detail", partId],
    queryFn: () => CatalogService.readPartDetail({ partId }),
  })
  if (part.isPending) return <p>Cargando pieza…</p>
  if (part.error) return <p role="alert">{fileErrorMessage(part.error)}</p>
  if (!isFolderAttachment(kind)) return <p>Galería no encontrada.</p>
  const files = savedFiles(part.data).filter((f) => f.kind === kind)
  return (
    <AttachmentDetail
      key={partId + kind}
      partId={partId}
      kind={kind}
      context={partLabel(part.data.part)}
      file={files.length === 1 ? files[0].file : undefined}
    />
  )
}
