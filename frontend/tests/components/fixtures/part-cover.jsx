import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { createRoot } from "react-dom/client"
import { CatalogService, FilesService } from "@/client"
import { PartThumbnail } from "../../../src/components/Parts/PartCover"

window.review = { captures: 0, saved: [] }
FilesService.uploadFile = async () => ({
  id: `image-${window.review.captures}`,
  filename: "piece.png",
  size: 10,
  content_type: "image/png",
})
CatalogService.savePartCover = async ({ requestBody }) => {
  window.review.saved.push(requestBody)
  return {
    id: requestBody.image_id,
    filename: "piece.png",
    size: 10,
    content_type: "image/png",
  }
}
FilesService.createFileAccessUrl = async ({ fileId }) => ({
  url: `/image/${fileId}.png`,
  expires_at: new Date(Date.now() + 900000).toISOString(),
})
const client = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Example() {
  const [version, setVersion] = useState("remote-v1")
  const part = {
    id: "part-one",
    code: "3212",
    name: "Test piece",
    cad_cache_key: version,
    cad: {
      id: "same-cad",
      version: "same-record",
      filename: "piece.stp",
      size: 100,
    },
  }
  return (
    <>
      <PartThumbnail part={part} />
      <button type="button" onClick={() => setVersion("remote-v2")}>
        Cambiar CAD remoto
      </button>
      <button type="button" onClick={() => setVersion(null)}>
        CAD no disponible
      </button>
    </>
  )
}

createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={client}>
    <Example />
  </QueryClientProvider>,
)
