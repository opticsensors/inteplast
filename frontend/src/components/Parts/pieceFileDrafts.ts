import { FileText } from "lucide-react"
import type {
  FilePublic,
  FolderDiscovery,
  PartDetailPublic,
  PartFileInput,
} from "@/client"
import { ASSET_ICONS, ASSET_KIND_LABELS } from "@/components/Features/constants"

export const FILE_LABELS = {
  ...ASSET_KIND_LABELS,
  document: "Documento / Otro",
}
export const FILE_ICONS = { ...ASSET_ICONS, document: FileText }
export const FILE_KINDS = [
  "part",
  "scan",
  "mold",
  "drawing",
  "moldflow",
  "document",
] as const
export const PRIMARY_KINDS = ["part", "scan", "mold", "drawing"] as const
export const canBePrimary = (kind: PartFileInput["kind"]) =>
  PRIMARY_KINDS.some((value) => value === kind)
export type FileDraft = PartFileInput & {
  key: string
  file?: FilePublic
  originalPath?: string | null
}

let nextDraftId = 0
// These keys identify unsaved UI rows, including installations served over LAN HTTP.
export const newFileKey = () => `draft-file-${++nextDraftId}`

export function normalizePrimaries(files: FileDraft[]): FileDraft[] {
  const chosen = new Map<string, string>()
  for (const file of files)
    if (canBePrimary(file.kind) && file.primary && !chosen.has(file.kind))
      chosen.set(file.kind, file.key)
  for (const file of files)
    if (canBePrimary(file.kind) && !chosen.has(file.kind))
      chosen.set(file.kind, file.key)
  return files.map((file) => ({
    ...file,
    primary: chosen.get(file.kind) === file.key,
  }))
}

export function savedFiles(data?: PartDetailPublic): FileDraft[] {
  const files =
    data?.files ??
    data?.references.map(({ kind, file }) => ({
      kind,
      file,
      name: file.filename,
      primary: canBePrimary(kind),
      path: undefined,
    })) ??
    []
  return files.map(({ file, name, kind, primary, path }) => ({
    key: file.id,
    file_id: file.id,
    file,
    name,
    kind,
    primary,
    originalPath: path,
  }))
}

export function discoveredFiles(folder: FolderDiscovery): FileDraft[] {
  return folder.references.flatMap(({ kind, path, source_version }) =>
    path
      ? [
          {
            key: newFileKey(),
            kind,
            path,
            source_version,
            name: path.split("/").pop()!,
            primary: true,
          },
        ]
      : [],
  )
}

export function guessFileKind(path: string): PartFileInput["kind"] {
  const ext = path.split(".").pop()?.toLowerCase()
  if (ext === "pdf") return "drawing"
  if (["stp", "step", "igs", "iges"].includes(ext ?? ""))
    return /mold|molde|mould/i.test(path) ? "mold" : "part"
  if (["stl", "obj", "ply", "glb", "gltf"].includes(ext ?? "")) return "scan"
  if (["mfr", "mpi"].includes(ext ?? "")) return "moldflow"
  return "document"
}

export const fileRequest = (files: FileDraft[]): PartFileInput[] =>
  files.map(({ key: _key, file: _file, originalPath: _path, ...choice }) => ({
    ...choice,
    name: choice.name.trim(),
  }))
