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
  /** `window.review.thumbnailBusy[fileId]`: how many times to answer "busy" first. */
  prepareThumbnail: async ({ fileId }) => {
    state().thumbnailRequests ??= []
    state().thumbnailRequests.push(fileId)
    const busy = state().thumbnailBusy ?? {}
    if (busy[fileId] > 0) {
      busy[fileId]--
      return { state: "busy", url: null }
    }
    return { state: "ready", url: `/thumbnails/${fileId}.png` }
  },
  readSourceTable: async ({ fileId }) => {
    if (state().tableError) throw new Error(state().tableError)
    return clone(state().sourceTables?.[fileId] ?? { sheets: [] })
  },
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
  readComponentOptions: async ({ partId }) => ({
    components: clone(state().organizations?.[partId] ?? []),
    unassigned: clone(state().unassignedSources?.[partId] ?? []),
    sources: [
      { path: "base.pdf", kind: "drawing" },
      { path: "cover.pdf", kind: "drawing" },
    ].concat(state().componentExtraSources ?? []),
    suggestions: [
      { key: "BASE", name: "BASE", sheets: ["DR(base)"], files: [] },
      { key: "TAPA", name: "TAPA", sheets: ["DR(tapa)"], files: [] },
    ],
    sheet_names: ["DR(base)", "DR(tapa)"].concat(
      state().componentExtraSheets ?? [],
    ),
    workbooks: [
      {
        path: "rev.A/report.xls",
        sheets: ["DR(base)", "DR(tapa)"].concat(
          state().componentExtraSheets ?? [],
        ),
      },
    ],
    unassigned_characteristics: 0,
  }),
  saveComponentOrganization: async ({ partId, requestBody }) => {
    state().organizations ??= {}
    state().organizations[partId] = clone(requestBody.components)
    state().unassignedSources ??= {}
    state().unassignedSources[partId] = clone(requestBody.unassigned ?? [])
    return clone(requestBody)
  },
  discoverPartFolder: async ({ requestBody }) => ({
    folder_path: requestBody.folder_path,
    name: requestBody.folder_path.split("/").pop(),
    code: requestBody.folder_path.split("/").pop().split(" ")[0],
    existing_part: clone(
      state().parts.find(
        (part) => part.folder_path === requestBody.folder_path,
      ) ?? null,
    ),
    references: ["part", "scan", "mold", "drawing"].map((kind) => ({
      kind,
      path: `${requestBody.folder_path}/${kind}.${kind === "drawing" ? "pdf" : kind === "scan" ? "stl" : "step"}`,
      candidates: [],
      source_version: "1:10",
    })),
    notices: [],
  }),
  registerPart: async ({ requestBody }) => {
    state().registrationRequests ??= []
    state().registrationRequests.push(clone(requestBody))
    if (state().failRegistration) throw new Error("No se pudo crear la pieza")
    const part = {
      ...clone(requestBody),
      id: `part-${state().parts.length + 1}`,
    }
    state().parts.push(part)
    setPieceFiles(part.id, requestBody.files)
    for (const featureId of requestBody.feature_ids ?? [])
      await FeaturesService.linkFeaturePart({ featureId, partId: part.id })
    return clone(part)
  },
  readPartDataReport: async ({ partId }) =>
    clone(state().readReports?.[partId] ?? null),
  readPartData: async ({ partId }) => {
    state().refreshRequests ??= []
    state().refreshRequests.push(partId)
    if (state().holdRefresh)
      await new Promise((resolve) => {
        state().releaseRefresh = resolve
      })
    if (state().failRead) throw new Error("No se pudo leer la carpeta")
    const report = {
      state: "ready",
      imported: 1,
      skipped: 0,
      corrections_state: "empty",
      measurements: { context_key: "test", files: [] },
      notices: [],
      updated_at: new Date().toISOString(),
      files: [
        {
          path: "rev.A/measurements.csv",
          group: "measurements",
          status: "imported",
        },
      ],
      ...state().nextReadReport,
    }
    state().readReports ??= {}
    state().readReports[partId] = report
    return clone(report)
  },
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
        ...clone(withCatalogNames(part)),
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
  readPartDeletion: async ({ partId }) => {
    const part = state().parts.find((item) => item.id === partId)
    return {
      part_id: partId,
      code: part.code,
      name: part.name,
      folder_path: part.folder_path ?? null,
      features: [],
      characteristics: 0,
      feature_characteristic_links: 0,
      measurement_imports: 0,
      feature_assets: 0,
      covers_reset: 0,
      files_removed: 0,
      uploads_removed: 0,
      files_kept: 0,
      reviewed_locations: 0,
      jobs: 0,
      key: `scope-of-${partId}`,
      ...clone(state().deletionScopes?.[partId] ?? {}),
    }
  },
  deletePart: async ({ partId, confirm }) => {
    state().partDeleteRequests ??= []
    state().partDeleteRequests.push(partId)
    if (confirm !== undefined) {
      state().partDeleteConfirms ??= []
      state().partDeleteConfirms.push(confirm)
    }
    if (state().holdPartDelete)
      await new Promise((resolve) => {
        state().releasePartDelete = resolve
      })
    if (state().failPartDelete) throw new Error("No se pudo eliminar la pieza")
    if (confirm === undefined && state().partUsage?.[partId])
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
    if (state().holdPartSave)
      await new Promise((resolve) => {
        state().releasePartSave = resolve
      })
    if (
      state().failParts ||
      state().parts.some(
        (part) => part.id !== partId && part.code === requestBody.code,
      )
    )
      throw new Error("No se pudo guardar la pieza")
    const part = state().parts.find((item) => item.id === partId)
    if (requestBody.files) setPieceFiles(partId, requestBody.files)
    if (requestBody.references) {
      state().partReferences ??= {}
      let references = state().partReferences[partId] ?? []
      for (const choice of requestBody.references) {
        references = references.filter(({ kind }) => kind !== choice.kind)
        if (choice.path)
          references.push({
            kind: choice.kind,
            file: {
              id: `file-${choice.kind}-${choice.path}`,
              filename: choice.path.split("/").pop(),
              source_path: choice.path,
              size: 1024,
              content_type: "application/octet-stream",
            },
          })
      }
      state().partReferences[partId] = references
    }
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
export const LoginService = {
  loginMethods: async () => ({
    password: !state().sharepoint,
    microsoft: Boolean(state().sharepoint),
    microsoft_paste: true,
    sharepoint: Boolean(state().sharepoint),
    source_name: "Test originals",
  }),
}

/** Shared lists of families and customers: same name ignoring case and spaces. */
const catalogNames = (kind) => {
  state()[kind] ??= []
  return state()[kind]
}
const catalogKey = (name) =>
  name.trim().split(/\s+/).join(" ").toLocaleLowerCase()
const addCatalogName = async (kind, { requestBody }) => {
  state().catalogNameRequests ??= []
  state().catalogNameRequests.push({ kind, name: requestBody.name })
  const name = requestBody.name.trim().split(/\s+/).join(" ")
  const list = catalogNames(kind)
  const existing = list.find(
    (item) => catalogKey(item.name) === catalogKey(name),
  )
  if (existing) return clone(existing)
  const created = { id: `${kind}-${list.length + 1}`, name }
  list.push(created)
  return clone(created)
}
const withCatalogNames = (part) => ({
  ...part,
  family:
    catalogNames("families").find((item) => item.id === part.family_id) ?? null,
  customer:
    catalogNames("customers").find((item) => item.id === part.customer_id) ??
    null,
})

export const CatalogService = {
  readFamilies: async () => ({
    data: clone(catalogNames("families")).sort((a, b) =>
      a.name.localeCompare(b.name),
    ),
  }),
  readCustomers: async () => ({
    data: clone(catalogNames("customers")).sort((a, b) =>
      a.name.localeCompare(b.name),
    ),
  }),
  createFamily: (data) => addCatalogName("families", data),
  createCustomer: (data) => addCatalogName("customers", data),
  searchCatalog: async (params = {}) => {
    const features =
      params.kind === "part"
        ? { data: [], count: 0 }
        : await FeaturesService.readFeatures(params)
    const parts =
      params.kind === "feature"
        ? { data: [], count: 0 }
        : await PartsService.readParts()
    // The server's criterion: a piece meets every piece filter at once.
    const pieceMatches = (part) =>
      (!params.partId || part.id === params.partId) &&
      (!params.familyId || part.family_id === params.familyId) &&
      (!params.customerId || part.customer_id === params.customerId)
    const filtered = params.familyId || params.customerId
    const shownParts = filtered ? parts.data.filter(pieceMatches) : parts.data
    const matching = new Set(shownParts.map((part) => part.id))
    const shownFeatures = filtered
      ? features.data.filter((feature) =>
          [
            ...(feature.parts ?? []),
            ...(feature.assets ?? []).map((asset) => asset.part),
          ].some((part) => part && matching.has(part.id)),
        )
      : features.data
    state().catalogRequests ??= []
    state().catalogRequests.push(clone(params))
    // Paged like the server; counts stay the totals.
    const page = (items) =>
      params.limit === undefined
        ? items
        : items.slice(params.skip ?? 0, (params.skip ?? 0) + params.limit)
    return {
      features: page(shownFeatures),
      parts: page(shownParts),
      cotas: [],
      feature_count: filtered ? shownFeatures.length : features.count,
      part_count: filtered ? shownParts.length : parts.count,
      cota_count: 0,
    }
  },
  /** Same results as the list; `window.review.graphLimit` forces the cut. */
  readCatalogGraph: async (params = {}) => {
    state().graphRequests ??= []
    state().graphRequests.push(clone(params))
    const list = await CatalogService.searchCatalog({ ...params, limit: 100 })
    const candidates = [
      ...list.parts.map((part) => ({
        id: `part:${part.id}`,
        kind: "part",
        ref_id: part.id,
        label: part.code,
        name: part.name ?? null,
        image: part.image ?? null,
      })),
      ...list.features.map((feature) => ({
        id: `feature:${feature.id}`,
        kind: "feature",
        ref_id: feature.id,
        label: feature.name,
      })),
    ]
    for (const group of ["family", "customer"])
      for (const part of list.parts) {
        const value = part[group]
        if (
          value &&
          !candidates.some((node) => node.id === `${group}:${value.id}`)
        )
          candidates.push({
            id: `${group}:${value.id}`,
            kind: group,
            ref_id: value.id,
            label: value.name,
          })
      }
    const nodes = candidates.slice(0, state().graphLimit ?? 500)
    const present = new Set(nodes.map((node) => node.id))
    const links = []
    for (const feature of list.features)
      for (const part of [
        ...(feature.parts ?? []),
        ...(feature.assets ?? []).map((asset) => asset.part),
      ])
        if (part)
          links.push({
            source: `part:${part.id}`,
            target: `feature:${feature.id}`,
            kind: "feature",
          })
    for (const part of list.parts)
      for (const group of ["family", "customer"])
        if (part[`${group}_id`])
          links.push({
            source: `part:${part.id}`,
            target: `${group}:${part[`${group}_id`]}`,
            kind: group,
          })
    return {
      nodes,
      links: links.filter(
        (link, index) =>
          present.has(link.source) &&
          present.has(link.target) &&
          links.findIndex(
            (other) =>
              other.source === link.source && other.target === link.target,
          ) === index,
      ),
      total: candidates.length,
      truncated: candidates.length > nodes.length,
    }
  },
  /** `window.review.drawings`: every drawing card, filtered like the server. */
  readCatalogDrawings: async (params = {}) => {
    state().drawingRequests ??= []
    state().drawingRequests.push(clone(params))
    const parts = (await PartsService.readParts()).data
    const matches = (card) => {
      const part = parts.find((item) => item.id === card.part.id)
      return (
        (!params.partId || card.part.id === params.partId) &&
        (!params.familyId || part?.family_id === params.familyId) &&
        (!params.customerId || part?.customer_id === params.customerId) &&
        (!params.q ||
          card.name.toLowerCase().includes(params.q.toLowerCase()) ||
          card.part.code.includes(params.q))
      )
    }
    const data = clone(state().drawings ?? []).filter(matches)
    const skip = params.skip ?? 0
    return {
      data: data.slice(skip, skip + (params.limit ?? 40)),
      count: data.length,
    }
  },
  readPartDetail: async ({ partId }) => ({
    part: (await PartsService.readParts()).data.find(
      (part) => part.id === partId,
    ),
    features: (await FeaturesService.readFeatures({ partId })).data,
    references: clone(state().partReferences?.[partId] ?? []),
    files: clone(state().pieceFiles?.[partId]),
  }),
}

function setPieceFiles(partId, files) {
  state().pieceFiles ??= {}
  const previous =
    state().pieceFiles[partId] ?? state().partReferences?.[partId] ?? []
  state().pieceFiles[partId] = files.map((item) => ({
    ...clone(item),
    file: item.file_id
      ? previous.find((row) => row.file.id === item.file_id).file
      : {
          id: `file-${item.path}`,
          filename: item.path.split("/").pop(),
          size: 1024,
          content_type: "application/octet-stream",
        },
  }))
  state().partReferences ??= {}
  state().partReferences[partId] = state()
    .pieceFiles[partId].filter((item) => item.primary)
    .map(({ kind, file }) => ({ kind, file }))
}
