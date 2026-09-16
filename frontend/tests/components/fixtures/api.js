// In-memory API only. The harness aborts every browser network request.
export const OpenAPI = { BASE: "https://files.invalid" }
export class ApiError extends Error {}
const clone = (value) => structuredClone(value)
const state = () => window.review

export const FeaturesService = {
  readFeature: async () => clone(state().feature),
  readFeatureFilters: async () => ({ parts: [], tags: [], categories: [] }),
  createFeatureNote: async ({ requestBody }) => {
    const note = {
      ...requestBody,
      id: `note-${state().feature.notes.length + 1}`,
    }
    state().feature.notes.push(note)
    return clone(note)
  },
  updateFeatureNote: async ({ noteId, requestBody }) => {
    state().requests.push({ kind: "note", patch: clone(requestBody) })
    if (state().delay)
      await new Promise((resolve) => setTimeout(resolve, state().delay))
    if (state().failNotes) throw new Error("Simulated save failure")
    const note = state().feature.notes.find((item) => item.id === noteId)
    Object.assign(note, requestBody)
    return clone(note)
  },
  updateFeatureAsset: async ({ assetId, requestBody }) => {
    state().requests.push({ kind: "asset", patch: clone(requestBody) })
    const asset = state().feature.assets.find((item) => item.id === assetId)
    Object.assign(asset, requestBody)
    if (requestBody.file_id && state().documents?.[requestBody.file_id])
      asset.file = clone(state().documents[requestBody.file_id])
    return clone(asset)
  },
  updateFeature: async ({ requestBody }) => {
    state().requests.push({ kind: "feature", patch: clone(requestBody) })
    Object.assign(state().feature, requestBody)
    return clone(state().feature)
  },
}

export const FilesService = {
  listSource: async ({ path }) => ({
    configured: true,
    name: "Test originals",
    path,
    count: 1,
    entries: path
      ? [
          {
            name: "drawing.pdf",
            path: "drawings/drawing.pdf",
            directory: false,
            size: 128,
          },
        ]
      : [{ name: "drawings", path: "drawings", directory: true }],
  }),
  referenceFile: async ({ requestBody }) => {
    if (state().failReferences) throw new Error("Source unavailable")
    state().referenceRequests ??= []
    state().referenceRequests.push(clone(requestBody))
    state().documents ??= {}
    const file = {
      id: "document-one",
      filename: "drawing.pdf",
      content_type: "application/pdf",
      size: 128,
      source: "local",
      version: "version-one",
      revision: requestBody.revision,
    }
    state().documents[file.id] = file
    return clone(file)
  },
  fileStatus: async () => ({
    state: state().fileState ?? "available",
    message:
      state().fileState === "missing"
        ? "Archivo no encontrado. Puedes volver a vincularlo."
        : "Disponible",
    path: "drawings/drawing.pdf",
  }),
  relinkFile: async ({ fileId, requestBody }) => {
    state().relinkRequests ??= []
    state().relinkRequests.push({ fileId, ...clone(requestBody) })
    const asset = state().feature.assets.find(
      (item) => item.file?.id === fileId,
    )
    asset.file = {
      ...asset.file,
      version: "version-two",
      revision: requestBody.revision,
    }
    state().fileState = "available"
    return clone(asset.file)
  },
  createFileAccessUrl: async ({ fileId }) => {
    state().accessRequests.push(fileId)
    return {
      url: `/api/v1/files/${fileId}?token=review-only`,
      expires_at: new Date(Date.now() + 900000).toISOString(),
    }
  },
  uploadFile: async ({ formData }) => {
    state().uploadRequests.push({
      filename: formData.file.name,
      contentType: formData.file.type,
    })
    if (state().holdUploads)
      await new Promise((resolve) => {
        state().releaseUpload = resolve
      })
    if (state().delay)
      await new Promise((resolve) => setTimeout(resolve, state().delay))
    if (state().failUploads) throw new Error("Upload unavailable")
    return {
      id: "uploaded-image",
      filename: formData.file.name,
      size: formData.file.size,
      content_type: formData.file.type,
    }
  },
}
export const PartsService = { readParts: async () => ({ data: [], count: 0 }) }
export const UsersService = {
  readUserMe: async () => ({
    id: "test-user",
    email: "review@example.com",
    is_superuser: false,
  }),
}
export const LoginService = {}
