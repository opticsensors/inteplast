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
    return clone(asset)
  },
  updateFeature: async ({ requestBody }) => {
    state().requests.push({ kind: "feature", patch: clone(requestBody) })
    Object.assign(state().feature, requestBody)
    return clone(state().feature)
  },
}

export const FilesService = {
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
    if (state().delay)
      await new Promise((resolve) => setTimeout(resolve, state().delay))
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
