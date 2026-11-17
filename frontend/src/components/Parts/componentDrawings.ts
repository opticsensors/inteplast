import type { PartEvidencePublic } from "@/client"

export const drawingNumber = (code?: string) => code?.split(":").slice(-1)[0]

export function componentDrawings(
  data: PartEvidencePublic | undefined,
  code?: string,
  revision?: string,
) {
  if (!data?.components?.length) return undefined
  const component = data.components.find((c) => c.key === code?.split(":")[0])
  if (!component) return []
  const paths = new Set(
    component.files
      ?.filter(
        (f) => f.revision === revision && f.path.toLowerCase().endsWith(".pdf"),
      )
      .map((f) => `${data.part.folder_path}/${f.path}`),
  )
  return data.documents.filter((d) => paths.has(d.relative_path ?? ""))
}
