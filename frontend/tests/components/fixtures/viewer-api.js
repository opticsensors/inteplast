export class ApiError extends Error {}
export const OpenAPI = { BASE: "" }
export const FilesService = {
  prepareThumbnail: async ({ page }) => ({
    state: "ready",
    rotation: location.hash === "#rotated" ? (page === 1 ? 90 : 270) : 0,
  }),
  createFileAccessUrl: async () => ({ url: "/original.pdf" }),
}
