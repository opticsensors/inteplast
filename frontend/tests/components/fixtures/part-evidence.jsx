import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router"
import { createRoot } from "react-dom/client"
import {
  CatalogService,
  EvidenceService,
  FeaturesService,
  PartsService,
} from "@/client"
import { PartDataImports } from "../../../src/components/Admin/PartDataImports"
import { Route as Catalog } from "../../../src/routes/_layout/features"
import { Route as Parts } from "../../../src/routes/_layout/parts"
import { Route as Detail } from "../../../src/routes/_layout/parts_.$partId"
import { Route as File } from "../../../src/routes/_layout/parts_.$partId_.fichero.$fileId"

const part = {
  id: "part-one",
  code: "3212",
  name: "Pump Housing",
  feature_count: 1,
  folder_path: "3212 Pump Housing",
}
const samples = ["01", "03", "05", "08"]
const cavities = ["c13", "c14", "c15", "c16"]
const source = {
  file_id: "source",
  path: "measurement.csv",
  locator: "Línea 2 · N170",
}
function series(id, block, idx, base = 3.975) {
  return {
    id,
    block,
    idx,
    label: `${block} · [${idx}] Medición`,
    unit: "mm",
    records: Object.fromEntries(
      cavities.map((cavity, cavityIndex) => [
        cavity,
        Object.fromEntries(
          samples.map((sample, sampleIndex) => [
            sample,
            {
              value:
                sampleIndex === 0
                  ? 3.429 + cavityIndex / 1000
                  : base + sampleIndex / 1000 + cavityIndex / 1000,
              lower: 3.9,
              upper: 4,
              status: sampleIndex === 0 ? "outside" : "inside",
              source,
            },
          ]),
        ),
      ]),
    ),
  }
}
const bolts = [1, 2, 3, 4].flatMap((bolt) =>
  ["1.5", "5.0"].flatMap((height) =>
    [1, 2].map((idx) =>
      series(
        `N170|B${bolt}-H${height}|${idx}`,
        "N170 BOLT 1 MIN/MAX",
        idx,
        idx === 1 ? 3.975 : 4.015,
      ),
    ),
  ),
)
if (window.evidenceSeparateCavities) bolts[0].records.c16["03"].value = 4.3
const pointSeries = ["GLOBAL 1.35 MIN/MAX", "POINT 1 MIN/MAX"].flatMap(
  (block) => [1, 2].map((idx) => series(`${block}|1|${idx}`, block, idx)),
)
const distance = series("N240 18.5 +0.2|1|1", "N240 18.5 +0.2", 1)
const diameter = [1, 2].map((idx) => {
  const item = series(`N161 45.4|1|${idx}`, "N161 45.4", idx)
  cavities.forEach((cavity, c) => {
    samples.forEach((sample, s) => {
      item.records[cavity][sample] = {
        ...item.records[cavity][sample],
        value: [45.82, 45.731, 45.396, 45.379][s] + c / 1000 + (idx - 1) * 0.08,
        lower: 45.4,
        upper: 45.55,
      }
    })
  })
  return item
})
const makeCase = (
  variants,
  seriesFor,
  title,
  actions,
  correction = "1",
  delta = 0.5,
) => ({
  title,
  variants,
  correction,
  actions,
  note: "",
  comparisons: Object.fromEntries(
    variants.map((variant) => [
      variant,
      Object.fromEntries(
        cavities.map((cavity) => [
          cavity,
          {
            warnings: [],
            items: seriesFor(variant).map((item, index) => ({
              label: index === 0 ? "GX" : "LP máximo",
              before: item.records[cavity][correction === "1" ? "01" : "03"],
              after: item.records[cavity][correction === "1" ? "03" : "05"],
              xls_before:
                item.records[cavity][correction === "1" ? "01" : "03"].value,
              prediction:
                item.records[cavity][correction === "1" ? "01" : "03"].value +
                delta,
              prediction_status: "inside",
              lower: 3.9,
              upper: 4,
              source,
              steps: [
                {
                  delta,
                  value:
                    item.records[cavity][correction === "1" ? "01" : "03"]
                      .value + delta,
                  cells: "O146",
                },
              ],
              history: samples.map((sample) => item.records[cavity][sample]),
            })),
          },
        ]),
      ),
    ]),
  ),
})
const variants = [1, 2, 3, 4].flatMap((bolt) =>
  ["1.5", "5.0"].map((height) => `B${bolt}-H${height}`),
)
const study = {
  samples,
  cavities,
  measurement_revision: "06",
  csv_count: 16,
  profiles: [],
  support: [],
  catalog: {
    entries: [
      {
        id: "N113",
        numbers: ["N113"],
        title: "N113 3+0.1 A 1",
        kind: "dimension",
        reviewed_case: null,
        series: [series("N113 3+0.1 A 1|1|1", "N113 3+0.1 A 1", 1)],
        actions: [],
      },
      {
        id: "N170",
        numbers: ["N170"],
        title: "Diámetro del Bolt Eye",
        kind: "dimension",
        reviewed_case: "N170",
        series: bolts,
        actions: ["1.33"],
      },
      {
        id: "N161",
        numbers: ["N161"],
        title: "Diámetro interior",
        kind: "dimension",
        reviewed_case: "N161",
        series: diameter,
        actions: ["1.31", "2.16"],
      },
      {
        id: "N165",
        numbers: ["N165"],
        title: "Espesor local",
        kind: "dimension",
        reviewed_case: "N165",
        series: pointSeries,
        actions: [],
      },
      {
        id: "N240",
        numbers: ["N240"],
        title: "Distancia al plano A",
        kind: "dimension",
        reviewed_case: null,
        series: [distance],
        actions: [],
      },
    ],
  },
  corrections: {
    1: { before: "01", after: "03", date: "24/01/2024" },
    2: { before: "03", after: "05", date: "18/03/2024" },
  },
  cases: {
    N170: makeCase(
      variants,
      (variant) => bolts.filter((item) => item.id.includes(`|${variant}|`)),
      "Diámetro del Bolt Eye",
      ["1.33"],
    ),
    N165: makeCase(
      ["main"],
      () => pointSeries.slice(0, 2),
      "Espesor local",
      [],
      "2",
      -0.22,
    ),
    N161: makeCase(
      ["main"],
      () => diameter,
      "Diámetro interior",
      ["2.16"],
      "2",
      -0.305,
    ),
  },
  actions: {
    1.33: {
      id: "1.33",
      paragraphs: ["Usar expulsores de 4 y revisar la posición."],
      images: [{ url: "proposal-image", width: 640, height: 480 }],
      source,
    },
  },
  action_index: {
    1.31: {
      id: "1.31",
      plan: "1",
      paragraphs: [
        "Tool correction 1.31",
        "Ajustar el diámetro interior según la zona marcada.",
      ],
      images: [],
      source,
    },
    2.16: {
      id: "2.16",
      plan: "2",
      paragraphs: [
        "Reducir el diámetro total 0,305 mm y conservar la redondez.",
      ],
      images: [],
      source,
    },
  },
}
study.cases.N170.description =
  "La propuesta plantea usar expulsores de Ø4 mm y revisar la posición."
study.cases.N161.description =
  "El plan propone reducir 0,305 mm en diámetro total y conservar la redondez."
window.review = {
  sourceTables: {
    source: {
      sheets: [
        {
          name: "CSV",
          rows: [
            ["N170", "", "", "", "", "", "c13", "c14", "c15", "c16"],
            [
              "16",
              "GX",
              "",
              "4",
              "0",
              "-0.1",
              "3.976",
              "3.977",
              "3.978",
              "3.979",
            ],
          ],
        },
      ],
    },
    excel: {
      sheets: [
        { name: "INTRO", rows: [["Informe"]] },
        {
          name: "DR_PAR",
          rows: Array.from({ length: 100 }, (_, row) =>
            row === 89
              ? ["N170", "", "", "4", "0", "-0.1", "CMM", "3.976"]
              : [],
          ),
        },
      ],
    },
  },
  accessRequests: [],
  sourceRequests: [],
  requests: [],
  study,
  imports: [],
}
EvidenceService.importPartEvidence = async ({ partId }) => {
  window.review.imports.push(partId)
  return { state: "ready", payload: study }
}
EvidenceService.readDrawingIndex = async () => ({
  state: "ready",
  reviews: [{ candidate_id: "reviewed", label: "N170.3" }],
  payload: {
    balloons: [
      {
        id: "base",
        page: 1,
        box: [20, 40, 40, 60],
        candidates: [{ label: "N170" }],
      },
      {
        id: "child",
        page: 1,
        box: [80, 100, 100, 120],
        candidates: [{ label: "N170.5" }],
      },
      {
        id: "reviewed",
        page: 2,
        box: [160, 180, 180, 200],
        candidates: [{ label: "N178" }],
      },
      { id: "unread", page: 1, box: [200, 220, 220, 240], candidates: [] },
      {
        id: "113",
        page: 1,
        box: [260, 280, 280, 300],
        candidates: [{ label: "N113" }],
      },
      {
        id: "113-copy",
        page: 2,
        box: [360, 380, 380, 400],
        candidates: [{ label: "N113" }],
      },
    ],
    words: [],
    notices: [],
  },
})
EvidenceService.reviewDrawingLocation = async () => {
  throw new Error("The consultation must not edit readings")
}
const secondPart = { ...part, id: "part-two", code: "3197", name: "Connector" }
const characteristic = (code, partId = part.id, revision = "06") => ({
  id: `${partId}-${code}-${revision}`,
  part_id: partId,
  revision,
  code,
  title: code,
  role: "primary",
})
const characteristics = ["N170", "N288", "N240"].map((code) =>
  characteristic(code),
)
const features = [
  {
    id: "bolt-eye",
    name: "Bolt Eye",
    category: "hole",
    tags: ["critical"],
    characteristics: characteristics.slice(0, 2),
    assets: [
      {
        id: "drawing-asset",
        part,
        kind: "drawing",
        file: {
          id: "linked-drawing",
          filename: "3212-07.pdf",
        },
      },
    ],
  },
  {
    id: "rib",
    name: "Rib",
    assets: [],
    category: "rib",
    tags: ["stiffness"],
    characteristics: [],
  },
  {
    id: "seal",
    name: "Seal",
    assets: [],
    category: "hole",
    tags: ["sealing"],
    characteristics: [characteristic("N113")],
  },
]
const catalog = [
  { part, features },
  {
    part: secondPart,
    features: [
      {
        id: "bolt-eye",
        name: "Bolt Eye",
        category: "hole",
        tags: ["critical"],
        characteristics: [characteristic("N170", secondPart.id, "04")],
      },
    ],
  },
]
EvidenceService.readMetrologyFilters = async () => ({
  parts: [
    ...catalog.map((item) => item.part),
    { id: "unused", code: "9000", name: "Sin features" },
  ],
  features: features.map(({ characteristics: _cotas, ...feature }) => ({
    ...feature,
    part_ids: catalog
      .filter((item) => item.features.some((f) => f.id === feature.id))
      .map((item) => item.part.id),
  })),
})
EvidenceService.readMetrology = async ({
  q = "",
  featureId,
  skip = 0,
  limit = 24,
}) => {
  const needle = q.toLowerCase()
  const foundFeatures = features.filter((feature) =>
    featureId
      ? feature.id === featureId
      : needle && feature.name.toLowerCase().includes(needle),
  )
  const data = catalog.flatMap((item) => {
    const linked = featureId
      ? item.features.filter((feature) => feature.id === featureId)
      : item.features
    const matches = linked.filter((feature) =>
      foundFeatures.some((match) => feature.id === match.id),
    )
    const pieceMatch = `${item.part.code} ${item.part.name}`
      .toLowerCase()
      .includes(needle)
    return (featureId ? linked.length : pieceMatch || matches.length)
      ? [
          {
            ...item,
            features: linked,
            matched_feature_ids:
              !featureId && pieceMatch
                ? []
                : matches.map((feature) => feature.id),
          },
        ]
      : []
  })
  return {
    data: data.slice(skip, skip + limit),
    count: data.length,
    features: foundFeatures,
  }
}
EvidenceService.readFeatureEvidence = async ({ featureId, partId }) => ({
  characteristics:
    catalog
      .find((item) => item.part.id === partId)
      ?.features.find((feature) => feature.id === featureId)?.characteristics ??
    [],
  pending: [],
  cases: [],
})
EvidenceService.readPartEvidence = async ({ partId, revision, snapshotId }) => {
  window.review.evidenceRequests ??= []
  window.review.evidenceRequests.push({ partId, revision, snapshotId })
  return {
    part: catalog.find((item) => item.part.id === partId).part,
    features: catalog.find((item) => item.part.id === partId).features,
    characteristics:
      partId === part.id
        ? characteristics
        : [characteristic("N170", secondPart.id, "04")],
    study: {
      state: "ready",
      payload: {
        ...study,
        measurement_revision: window.review.measurementRevisions?.includes(
          revision,
        )
          ? revision
          : study.measurement_revision,
      },
    },
    measurement_revisions: window.review.measurementRevisions ?? [],
    import_available: true,
    drawing_reference_set: window.review.drawingRemoved ?? false,
    documents: [
      {
        id: "source",
        filename: "measurement.csv",
        content_type: "text/csv",
        version: "v1",
        source: "upload",
      },
      {
        id: "excel",
        filename: "report.xlsx",
        content_type:
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        version: "v1",
        source: "upload",
      },
      {
        id: "linked-drawing",
        filename: "3212-07.pdf",
        content_type: "application/pdf",
        version: "v1",
        source: "upload",
      },
      {
        id: "drawing",
        filename: "DRW_3212.pdf",
        size: 123456,
        content_type: "application/pdf",
        version: "v1",
        source: "upload",
      },
    ],
  }
}
PartsService.readParts = async () => ({ data: [part, secondPart], count: 2 })
FeaturesService.readFeatureFilters = async () => ({
  ...(await EvidenceService.readMetrologyFilters()),
  categories: ["hole", "rib"],
  tags: ["critical", "stiffness", "sealing"],
})
CatalogService.readPartDetail = async ({ partId }) => {
  const item = catalog.find((item) => item.part.id === partId)
  return {
    part: {
      ...item.part,
      characteristic_count:
        item.part.id === part.id ? characteristics.length : 1,
      feature_count: item.features.length,
    },
    features: item.features,
    references: [
      {
        kind: "drawing",
        file: {
          id: "drawing",
          filename: "DRW_3212.pdf",
          size: 123456,
          content_type: "application/pdf",
          version: "v1",
          source: "upload",
        },
      },
    ],
  }
}
CatalogService.searchCatalog = async ({ kind, featureId }) => {
  const parts = catalog
    .filter(
      (item) =>
        !featureId || item.features.some((feature) => feature.id === featureId),
    )
    .map((item) => item.part)
  return {
    parts,
    features: kind === "part" ? [] : features,
    cotas: [],
    part_count: parts.length,
    feature_count: kind === "part" ? 0 : features.length,
    cota_count: 0,
  }
}
const root = createRootRoute({ component: () => <Outlet /> })
const layout = createRoute({
  id: "_layout",
  getParentRoute: () => root,
  component: () => <Outlet />,
})
const routes = [
  [Catalog, "/features", "/features"],
  [Parts, "/parts", "/parts"],
  [Detail, "/parts_/$partId", "/parts/$partId"],
  [File, "/parts_/$partId_/fichero/$fileId", "/parts/$partId/fichero/$fileId"],
].map(([route, id, path]) =>
  route.update({ id, path, getParentRoute: () => layout }),
)
const router = createRouter({
  routeTree: root.addChildren([
    layout.addChildren([
      ...routes,
      createRoute({
        path: "/manage-test",
        getParentRoute: () => layout,
        component: () => (
          <>
            <h1>Gestión de datos</h1>
            <PartDataImports />
          </>
        ),
      }),
    ]),
  ]),
  history: createMemoryHistory({
    initialEntries: [window.evidenceInitialPath ?? "/parts/part-one"],
  }),
})
window.review.location = () => router.state.location
window.review.navigate = (options) => router.navigate(options)
window.review.back = () => router.history.back()
window.review.forward = () => router.history.forward()
const client = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})
window.review.refetchEvidence = () =>
  client.invalidateQueries({ queryKey: ["part-evidence"] })
createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={client}>
    <RouterProvider router={router} />
  </QueryClientProvider>,
)
