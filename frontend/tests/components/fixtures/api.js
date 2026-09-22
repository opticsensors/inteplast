// In-memory API only. The harness aborts every browser network request.
export const OpenAPI = { BASE: "https://files.invalid" }
export class ApiError extends Error {}
export const EvidenceService = {
  readMetrologyFilters: async () => FeaturesService.readFeatureFilters(),
  readFeatureEvidence: async ({ partId }) => ({
    characteristics: clone(
      (state().characteristics ?? []).filter((item) => item.part_id === partId),
    ),
    pending: [],
    cases: [],
  }),
  readPartEvidence: async ({ partId }) => ({
    features: [],
    documents: [],
    characteristics: clone(
      [
        ...(state().characteristics ?? []),
        ...(state().importedCharacteristics ?? []),
      ].filter((item) => item.part_id === partId),
    ),
    measurement_revisions: state().measurementRevisions ?? [],
    study: {
      state: "ready",
      payload: {
        measurement_revision:
          state().measurementRevision === undefined
            ? "06"
            : state().measurementRevision,
      },
    },
  }),
  measurementHistory: async () => [],
  previewMeasurements: async ({ requestBody }) => {
    state().previewRequests ??= []
    state().previewRequests.push(clone(requestBody))
    return {
      context_key: "preview-context",
      files: (requestBody.files.length
        ? requestBody.files
        : (state().csvFiles ?? [])
      ).map((file) => ({
        ...file,
        status:
          file.revision && file.sample && file.cavity ? "new" : "needs_context",
        rows: 2,
        cotas: 1,
        issues: [],
        examples: [
          {
            numbers: ["N170"],
            nominal: 4,
            tol_inf: -0.1,
            tol_sup: 0,
            value: 3.95,
            unit: "mm",
          },
        ],
      })),
      notices: [],
    }
  },
  importMeasurements: async ({ partId, requestBody }) => {
    state().measurementImports ??= []
    state().measurementImports.push(clone(requestBody))
    state().measurementRevisions = requestBody.files.map(
      (file) => file.revision,
    )
    state().importedCharacteristics = requestBody.files.map((file, index) => ({
      id: `imported-${index}`,
      part_id: partId,
      code: "N170",
      revision: file.revision,
      title: "Diámetro",
    }))
    return {
      imported: requestBody.files.length,
      skipped: 0,
      revisions: state().measurementRevisions,
    }
  },
  assignCharacteristic: async ({ partId, requestBody }) => {
    state().characteristicRequests ??= []
    state().characteristicRequests.push(clone(requestBody))
    if (state().failCharacteristics)
      throw new Error("Simulated characteristic save failure")
    if (state().holdCharacteristics)
      await new Promise((resolve) => {
        state().releaseCharacteristics = resolve
      })
    state().characteristics ??= []
    let item = state().characteristics.find(
      (item) =>
        item.part_id === partId &&
        item.code === requestBody.code &&
        item.revision === requestBody.revision,
    )
    if (!item) {
      item = {
        ...requestBody,
        part_id: partId,
        id: crypto.randomUUID(),
        title: "",
      }
      state().characteristics.push(item)
    }
    item.role = requestBody.role
    return clone(item)
  },
  unassignCharacteristic: async ({ characteristicId }) => {
    if (state().failCharacteristicRemove)
      throw new Error("Simulated characteristic removal failure")
    state().characteristics = state().characteristics.filter(
      (item) => item.id !== characteristicId,
    )
  },
}
const clone = (value) => structuredClone(value)
const state = () => window.review

export const FeaturesService = {
  createFeature: async ({ requestBody }) => {
    state().featureCreateRequests ??= []
    state().featureCreateRequests.push(clone(requestBody))
    if (state().holdFeatureCreate)
      await new Promise((resolve) => {
        state().releaseFeatureCreate = resolve
      })
    if (state().failFeatureCreate)
      throw new Error("No se pudo crear el feature")
    state().feature = {
      ...requestBody,
      id: "created-feature",
      notes: [],
      assets: [],
      parts: [],
      part_order: [],
    }
    return clone(state().feature)
  },
  readFeature: async () => clone(state().feature),
  readFeatureFilters: async () => ({
    parts: [],
    features: [],
    tags: [],
    categories: [],
  }),
  createFeatureNote: async ({ featureId, requestBody }) => {
    if (featureId !== state().feature.id) throw new Error("Unknown feature")
    const note = {
      ...requestBody,
      id: `note-${state().feature.notes.length + 1}`,
    }
    state().feature.notes.push(note)
    return clone(note)
  },
  linkFeaturePart: async ({ featureId, partId }) => {
    if (featureId !== state().feature.id) throw new Error("Unknown feature")
    if (state().failPartLinks) throw new Error("Simulated link failure")
    const part = state().parts.find((item) => item.id === partId)
    if (!state().feature.parts.some((item) => item.id === partId))
      state().feature.parts.push(clone(part))
    state().feature.part_order ??= state().feature.parts.map((item) => item.id)
    if (!state().feature.part_order.includes(partId))
      state().feature.part_order.push(partId)
    return clone(state().feature)
  },
  unlinkFeaturePart: async ({ partId }) => {
    state().feature.parts = state().feature.parts.filter(
      (part) => part.id !== partId,
    )
    state().feature.assets = state().feature.assets.filter(
      (asset) => asset.part?.id !== partId,
    )
    state().feature.part_order = (state().feature.part_order ?? []).filter(
      (id) => id !== partId,
    )
  },
  reorderFeatureParts: async ({ requestBody }) => {
    if (state().failReorder) throw new Error("Simulated order failure")
    state().feature.part_order = clone(requestBody.part_ids)
    return clone(state().feature)
  },
  reorderFeatureNotes: async ({ requestBody }) => {
    if (state().failReorder) throw new Error("Simulated order failure")
    requestBody.note_ids.forEach((id, position) => {
      state().feature.notes.find((note) => note.id === id).position = position
    })
    return { message: "Order saved" }
  },
  reorderFeatureAssets: async ({ requestBody }) => {
    if (state().failReorder) throw new Error("Simulated order failure")
    requestBody.asset_ids.forEach((id, position) => {
      state().feature.assets.find((asset) => asset.id === id).position =
        position
    })
    return { message: "Order saved" }
  },
  createFeatureAsset: async ({ requestBody }) => {
    const asset = {
      ...requestBody,
      id: `asset-${state().feature.assets.length + 1}`,
      part: clone(
        state().feature.parts.find((part) => part.id === requestBody.part_id),
      ),
      file: null,
    }
    state().feature.assets.push(asset)
    return clone(asset)
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
    if (asset.file) asset.name = asset.file.filename
    return clone(asset)
  },
  updateFeature: async ({ requestBody }) => {
    state().requests.push({ kind: "feature", patch: clone(requestBody) })
    Object.assign(state().feature, requestBody)
    return clone(state().feature)
  },
}

export const FilesService = {
  listSource: async ({ path, directoriesOnly, skip = 0, limit = 200 }) => {
    state().sourceRequests ??= []
    state().sourceRequests.push({ path, directoriesOnly, skip })
    if (state().failSource) throw new Error("Source unavailable")
    if (!path && directoriesOnly) {
      const entries = (
        state().sourceFolders ?? [
          "2820 Pump Housing",
          "3051 Pump Housing",
          "3197 Pot",
          "3212 Pump Housing",
        ]
      ).map((name) => ({ name, path: name, directory: true }))
      return {
        configured: state().sourceConfigured ?? true,
        name: "Test originals",
        path,
        count: entries.length,
        entries: entries.slice(skip, skip + limit),
      }
    }
    return {
      configured: true,
      name: "Test originals",
      path,
      count: path && directoriesOnly ? 0 : 1,
      entries: path
        ? directoriesOnly
          ? []
          : [
              {
                name: "drawing.pdf",
                path: "drawings/drawing.pdf",
                directory: false,
                size: 128,
              },
            ]
        : [{ name: "drawings", path: "drawings", directory: true }],
    }
  },
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
    const uploaded = {
      id: "uploaded-image",
      filename: formData.file.name,
      size: formData.file.size,
      content_type: formData.file.type,
    }
    state().documents ??= {}
    state().documents[uploaded.id] = clone(uploaded)
    return uploaded
  },
}
export const PartsService = {
  discoverPartFolder: async ({ requestBody }) => ({
    folder_path: requestBody.folder_path,
    name: requestBody.folder_path.split("/").pop(),
    references: ["part", "scan", "mold", "drawing"].map((kind) => ({
      kind,
      path: `${requestBody.folder_path}/${kind}.${kind === "drawing" ? "pdf" : kind === "scan" ? "stl" : "step"}`,
      candidates: [],
      source_version: "1:10",
    })),
    notices: [],
  }),
  setupPart: async ({ requestBody }) => {
    const part = await PartsService.createPartFromFolder({ requestBody })
    part.name = requestBody.name
    state().setupRequests ??= []
    state().setupRequests.push(clone(requestBody))
    return { part }
  },
  refreshPartData: async ({ partId }) => {
    state().refreshRequests ??= []
    state().refreshRequests.push(partId)
    if (state().holdRefresh)
      await new Promise((resolve) => {
        state().releaseRefresh = resolve
      })
    return {
      imported: 0,
      skipped: 0,
      corrections_state: "empty",
      notices: [],
      measurements: await EvidenceService.previewMeasurements({
        requestBody: { files: [] },
      }),
    }
  },
  createPartFromFolder: async ({ requestBody: { folder_path } }) => {
    state().folderRequests ??= []
    state().folderRequests.push(folder_path)
    const existing = state().parts.find(
      (part) => part.folder_path === folder_path,
    )
    if (existing) return clone(existing)
    const code =
      /^(\d+)(?:[\s_-]|$)/.exec(folder_path)?.[1] ?? `PIEZA-${folder_path}`
    const legacy = state().parts.find(
      (part) => part.code === code && !part.folder_path,
    )
    if (legacy) {
      legacy.folder_path = folder_path
      return clone(legacy)
    }
    const part = {
      id: `part-${state().parts.length + 1}`,
      code,
      name: folder_path,
      folder_path,
    }
    state().parts.push(part)
    return clone(part)
  },
  readParts: async () => {
    state().parts ??= clone(state().feature.parts)
    return {
      data: state().parts.map((part) => ({
        ...clone(part),
        feature_count:
          (state().partUsage?.[part.id] ?? 0) +
          Number(
            state().feature.parts.some((linked) => linked.id === part.id) ||
              state().feature.assets.some(
                (asset) => asset.part?.id === part.id,
              ),
          ),
      })),
      count: state().parts.length,
    }
  },
  deletePart: async ({ partId }) => {
    state().partDeleteRequests ??= []
    state().partDeleteRequests.push(partId)
    if (state().holdPartDelete)
      await new Promise((resolve) => {
        state().releasePartDelete = resolve
      })
    if (state().failPartDelete) throw new Error("No se pudo eliminar la pieza")
    if (state().partUsage?.[partId])
      throw Object.assign(
        new ApiError("Pieza usada en otro feature. Desvinculala primero."),
        { status: 409 },
      )
    state().parts = state().parts.filter((part) => part.id !== partId)
  },
  createPart: async ({ requestBody }) => {
    if (state().createPartConflicts > 0) {
      state().createPartConflicts--
      throw Object.assign(new ApiError("Codigo duplicado"), { status: 409 })
    }
    const part = { ...requestBody, id: `part-${state().parts.length + 1}` }
    state().parts.push(part)
    return clone(part)
  },
  updatePart: async ({ partId, requestBody }) => {
    state().requests.push({ kind: "part", patch: clone(requestBody) })
    if (
      state().failParts ||
      state().parts.some(
        (part) => part.id !== partId && part.code === requestBody.code,
      )
    )
      throw new Error("No se pudo guardar la pieza")
    const part = state().parts.find((item) => item.id === partId)
    if (
      requestBody.folder_path != null &&
      (!part.name ||
        part.name === "Nueva pieza" ||
        part.name === part.folder_path?.split("/").pop())
    )
      requestBody.name ??=
        requestBody.folder_path.split("/").pop() || "Test originals"
    Object.assign(part, requestBody)
    for (const linked of state().feature.parts)
      if (linked.id === partId) Object.assign(linked, requestBody)
    for (const asset of state().feature.assets)
      if (asset.part?.id === partId) Object.assign(asset.part, requestBody)
    return clone(part)
  },
}
export const UsersService = {
  readUserMe: async () => ({
    id: "test-user",
    email: "review@example.com",
    is_superuser: state().isSuperuser ?? false,
  }),
}
export const LoginService = {}

export const CatalogService = {
  searchCatalog: async (params = {}) => {
    const features =
      params.kind === "part"
        ? { data: [], count: 0 }
        : await FeaturesService.readFeatures(params)
    const parts =
      params.kind === "feature"
        ? { data: [], count: 0 }
        : await PartsService.readParts()
    return {
      features: features.data,
      parts: parts.data,
      cotas: [],
      feature_count: features.count,
      part_count: parts.count,
      cota_count: 0,
    }
  },
  readPartDetail: async ({ partId }) => ({
    part: (await PartsService.readParts()).data.find(
      (part) => part.id === partId,
    ),
    features: (await FeaturesService.readFeatures({ partId })).data,
    references: [],
  }),
}
