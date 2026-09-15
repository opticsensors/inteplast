export class ApiError extends Error {}
export const OpenAPI = { BASE: "" }
export const FilesService = {
  preparePreview: async (options) => {
    window.preview.calls.push(options)
    const state = window.preview.states[0]
    if (window.preview.states.length > 1) window.preview.states.shift()
    return state
  },
  createFileAccessUrl: () => {
    throw new Error("Original must not be requested")
  },
}
