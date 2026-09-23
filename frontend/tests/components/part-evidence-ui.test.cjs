const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { before, after, test } = require("node:test")
const { chromium, expect } = require("@playwright/test")

const frontend = path.resolve(__dirname, "../..")
const artifacts = path.join(
  os.homedir(),
  ".codex",
  "scratch",
  "inteplast-cotas-ui",
)
let server, browser, origin
before(async () => {
  const [{ createServer }, { default: tailwindcss }] = await Promise.all([
    import("vite"),
    import("@tailwindcss/vite"),
  ])
  server = await createServer({
    configFile: false,
    root: frontend,
    logLevel: "error",
    cacheDir: path.join(artifacts, "vite", String(process.pid)),
    optimizeDeps: {
      entries: [path.join(__dirname, "fixtures/part-evidence.jsx")],
    },
    esbuild: { jsx: "automatic" },
    resolve: {
      alias: [
        {
          find: "./PdfViewer",
          replacement: path.join(__dirname, "fixtures/evidence-drawing.jsx"),
        },
        {
          find: "@/client",
          replacement: path.join(__dirname, "fixtures/api.js"),
        },
        { find: "@", replacement: path.join(frontend, "src") },
      ],
    },
    server: { host: "127.0.0.1", port: 0 },
    plugins: [
      tailwindcss(),
      {
        name: "evidence-page",
        configureServer(vite) {
          vite.middlewares.use("/evidence-test", async (_req, res, next) => {
            try {
              const html = await vite.transformIndexHtml(
                "/evidence-test",
                '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><main id="root" style="max-width:1120px;margin:24px auto;padding:0 20px"></main><script type="module" src="/tests/components/fixtures/part-evidence.jsx"></script></body></html>',
              )
              res.setHeader("Content-Type", "text/html")
              res.end(html)
            } catch (error) {
              next(error)
            }
          })
        },
      },
    ],
  })
  await server.listen()
  origin = `http://127.0.0.1:${server.httpServer.address().port}`
  browser = await chromium.launch({ headless: true })
  fs.mkdirSync(artifacts, { recursive: true })
})
after(async () => {
  await browser?.close()
  await server?.close()
})

async function mount(
  t,
  initial = "/parts/part-one?cota=N170",
  mobile = false,
  separateCavities = false,
) {
  const page = await browser.newPage({
    viewport: mobile
      ? { width: 390, height: 844 }
      : { width: 1200, height: 950 },
    hasTouch: mobile,
  })
  t.after(() => page.close())
  const errors = []
  page.on("pageerror", (error) => errors.push(error.message))
  t.after(() => assert.deepEqual(errors, []))
  await page.route("**/*", (route) =>
    route.request().url().startsWith(origin) ? route.continue() : route.abort(),
  )
  await page.addInitScript(
    ({ initial, separateCavities }) => {
      window.evidenceInitialPath = initial
      window.evidenceSeparateCavities = separateCavities
    },
    { initial, separateCavities },
  )
  await page.goto(`${origin}/evidence-test`)
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  return page
}
const state = (page) => page.evaluate(() => window.review.location().search)

test("revision and historical import survive revision changes and browser navigation", async (t) => {
  const page = await mount(
    t,
    "/parts/part-one?revision=06&snapshot=older-import",
  )
  await page.evaluate(async () => {
    window.review.measurementRevisions = ["06", "07"]
    await window.review.refetchEvidence()
  })
  await expect(
    page.getByText("Consulta de una importación anterior."),
  ).toBeVisible()
  assert.deepEqual(
    await page.evaluate(() => window.review.evidenceRequests.at(-1)),
    {
      partId: "part-one",
      revision: "06",
      snapshotId: "older-import",
    },
  )
  assert.equal((await state(page)).snapshot, "older-import")
  await page
    .getByRole("combobox", { name: "Revisión de mediciones", exact: true })
    .click()
  await page.getByRole("option", { name: "07", exact: true }).click()
  await expect(
    page.getByText("Consulta de una importación anterior."),
  ).toHaveCount(0)
  await expect
    .poll(() =>
      page.evaluate(() => window.review.evidenceRequests.at(-1).revision),
    )
    .toBe("07")
  assert.equal((await state(page)).snapshot, undefined)
  await page.evaluate(() => window.review.back())
  await expect(
    page.getByText("Consulta de una importación anterior."),
  ).toBeVisible()
  assert.equal((await state(page)).revision, "06")
})

test("a single consultation can start with a feature and then choose its piece", async (t) => {
  const page = await mount(t, "/parts")
  await expect(page.getByRole("heading", { name: "Catálogo" })).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Abrir Pump Housing" }),
  ).toBeVisible()
  await expect(
    page.getByRole("combobox", { name: "Buscar cota", exact: true }),
  ).toHaveCount(0)
  await page.getByRole("button", { name: "Filtros", exact: true }).click()
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  const featureSearch = page.getByRole("combobox", {
    name: "Buscar feature",
    exact: true,
  })
  await featureSearch.fill("bolt")
  await featureSearch.press("Enter")
  await page.getByRole("button", { name: "Abrir Pump Housing" }).click()
  await expect(
    page.getByRole("heading", { name: "Pump Housing", exact: true }),
  ).toBeVisible()
  await expect(page.getByRole("combobox", { name: "Buscar cota" })).toHaveValue(
    "",
  )
  assert.equal((await state(page)).feature, "bolt-eye")
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
  const choices = page.getByRole("group", { name: "Cotas disponibles" })
  await expect(choices).toHaveCount(0)
  await page.getByRole("combobox", { name: "Buscar cota" }).fill("N")
  assert.deepEqual(await choices.getByRole("button").allTextContents(), [
    "N113",
    "N161",
    "N165",
    "N170",
    "N240",
    "N288",
  ])
  await page.getByRole("option", { name: /^N170/ }).click()
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Correcciones", exact: true }).click()
  const selected = await state(page)
  await page.screenshot({
    path: path.join(artifacts, "metrology-feature-detail.png"),
    fullPage: true,
  })
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await expect(page.getByRole("status")).toHaveText("3 resultados")
  await page
    .getByRole("textbox", { name: "Buscar cota en el plano" })
    .fill("N113")
  await expect(page.getByRole("status")).toHaveText("2 resultados")
  await page.evaluate(() => window.review.back())
  await expect(
    page.getByRole("combobox", { name: "Buscar cota" }),
  ).toBeVisible()
  assert.deepEqual(await state(page), selected)
  await page.evaluate(() => window.review.forward())
  await expect(
    page.getByRole("textbox", { name: "Buscar cota en el plano" }),
  ).toHaveValue("N113")
  await page.evaluate(() => window.review.back())
  assert.deepEqual(await state(page), selected)
  await page
    .getByRole("region", { name: "Feature Bolt Eye", exact: true })
    .getByRole("button", { name: "N288", exact: true })
    .click()
  await expect(
    page.getByText(
      "Esta cota no tiene mediciones incorporadas. Puedes consultarla en el plano.",
    ),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toBeEnabled()
  const search = page.getByRole("combobox", {
    name: "Buscar cota",
    exact: true,
  })
  await search.fill("N240")
  await search.press("Enter")
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
  assert.equal((await state(page)).feature, undefined)
  await expect(
    page
      .getByRole("region", { name: "Feature Rib", exact: true })
      .getByText("Sin cotas vinculadas"),
  ).toBeVisible()
})

test("a piece starts without an arbitrary cota and includes unassigned cotas on mobile", async (t) => {
  const page = await mount(t, "/parts/part-one", true)
  const search = page.getByRole("combobox", { name: "Buscar cota" })
  await expect(search).toHaveValue("")
  const chart = page.getByRole("region", { name: "Evolución de mediciones" })
  const emptyPlot = chart.getByRole("img", {
    name: "Gráfica de mediciones sin cota seleccionada",
  })
  await expect(emptyPlot).toBeVisible()
  await expect(
    page.getByRole("group", { name: "Cotas disponibles" }),
  ).toHaveCount(0)
  await expect(
    chart.getByRole("group", { name: "Cavidades visibles" }),
  ).toHaveCount(0)
  await expect(emptyPlot.locator("circle, rect")).toHaveCount(0)
  assert.deepEqual(await emptyPlot.locator("text").allTextContents(), [
    "intern.01",
    "intern.03",
    "intern.05",
    "intern.08",
  ])
  await expect(
    page.getByRole("combobox", { name: /^(Elemento|Altura|Evaluación)$/ }),
  ).toHaveCount(0)
  const emptySize = await emptyPlot.boundingBox()
  await page.screenshot({
    path: path.join(artifacts, "piece-empty-plot-mobile.png"),
    fullPage: true,
  })
  await page.evaluate(async () => {
    const entry = window.review.study.catalog.entries.find(
      (entry) => entry.id === "N240",
    )
    for (const series of entry.series)
      for (const records of Object.values(series.records)) delete records["08"]
    await window.review.refetchEvidence()
  })
  await search.fill("N240")
  await page.getByRole("option", { name: /^N240/ }).click()
  await expect(search).toHaveValue("N240")
  assert.deepEqual(await chart.locator("svg text[y='263']").allTextContents(), [
    "intern.01",
    "intern.03",
    "intern.05",
  ])
  const feature = page.getByRole("region", {
    name: "Feature Bolt Eye",
    exact: true,
  })
  await feature.getByRole("button", { name: "N170", exact: true }).click()
  await expect(search).toHaveValue("N170")
  const selectedPlot = chart.getByRole("img", {
    name: "Gráfica de mediciones en mm",
  })
  await expect(selectedPlot).toBeVisible()
  const selectedSize = await selectedPlot.boundingBox()
  assert.equal(selectedSize.width, emptySize.width)
  assert.equal(selectedSize.height, emptySize.height)
  assert.deepEqual(
    await selectedPlot.locator("text[y='263']").allTextContents(),
    ["intern.01", "intern.03", "intern.05", "intern.08"],
  )
  await expect(
    chart.getByRole("group", { name: "Cavidades visibles" }),
  ).toBeVisible()
  await expect(
    page.getByRole("combobox", { name: "Feature", exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: "Más filtros", exact: true }),
  ).toHaveCount(0)
  await page.screenshot({
    path: path.join(artifacts, "piece-features-mobile.png"),
    fullPage: true,
  })
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await search.fill("N240")
  await search.press("Enter")
  assert.equal((await state(page)).cota, "N240")
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
  await feature
    .getByRole("link", { name: "Buscar N170 en el plano", exact: true })
    .click()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "3212-07.pdf",
  )
  await expect(
    page.getByRole("textbox", { name: "Buscar cota en el plano" }),
  ).toHaveValue("N170")
  assert.equal(
    await page.evaluate(() => window.review.location().pathname),
    "/parts/part-one/fichero/linked-drawing",
  )
  assert.equal((await state(page)).revision, "06")
  assert.equal((await state(page)).feature, "bolt-eye")
  await page.evaluate(() => window.review.back())
  await expect(search).toHaveValue("N240")
})

test("identical numbers in another piece do not use an incompatible measurement revision", async (t) => {
  const page = await mount(
    t,
    "/parts/part-two?feature=bolt-eye&cota=N170&revision=04",
  )
  await expect(
    page.getByRole("heading", { name: "Connector", exact: true }),
  ).toBeVisible()
  assert.equal((await state(page)).revision, "04")
  await expect(
    page.getByText(/No hay mediciones de esta cota para la revisión vinculada/),
  ).toBeVisible()
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("combobox", { name: "Pieza", exact: true }),
  ).toHaveCount(0)
})

test("legacy feature filters do not hide an unassigned cota in the piece", async (t) => {
  const page = await mount(t, "/parts/part-one?feature=bolt-eye&cota=N240")
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
})

async function choose(page, label, value) {
  await page.getByRole("combobox", { name: label, exact: true }).click()
  await page.getByRole("option", { name: value, exact: true }).click()
}

test("the piece's drawing file opens its own page and Back restores the piece", async (t) => {
  const page = await mount(
    t,
    "/parts/part-one?cota=N170&view=correcciones&interval=03-05",
  )
  const previous = await state(page)
  await page.getByRole("link", { name: "DRW_3212.pdf", exact: true }).click()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "DRW_3212.pdf",
  )
  await expect(
    page.getByRole("region", { name: "Plano de prueba" }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.location().pathname),
    "/parts/part-one/fichero/drawing",
  )
  await expect(
    page.getByRole("region", { name: "Cotas de la pieza" }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("textbox", { name: "Buscar cota en el plano" }),
  ).toHaveValue("")
  await page.evaluate(() => window.review.back())
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Pump Housing",
  )
  assert.deepEqual(await state(page), previous)
})

test("an explicitly removed drawing is not recovered automatically from historical documents", async (t) => {
  const page = await mount(t)
  const drawing = page.getByRole("button", { name: "Plano", exact: true })
  await expect(drawing).toBeEnabled()
  await page.evaluate(async () => {
    window.review.drawingRemoved = true
    await window.review.refetchEvidence()
  })
  await expect(drawing).toBeDisabled()
})

test("a feature's drawing link keeps the actual PDF even when its filename lacks a drawing label", async (t) => {
  const page = await mount(
    t,
    "/parts/part-one?feature=bolt-eye&cota=N170&plano=true&drawingFile=linked-drawing",
  )
  await expect(
    page.getByRole("region", { name: "Plano de prueba" }),
  ).toBeVisible()
  await expect(page.getByRole("status")).toHaveText("3 resultados")
  assert.equal(
    await page.evaluate(() => window.review.drawingFile),
    "linked-drawing",
  )
  assert.equal(
    await page.evaluate(() => window.review.location().pathname),
    "/parts/part-one/fichero/linked-drawing",
  )
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "3212-07.pdf",
  )
  await expect(
    page.getByRole("region", { name: "Cotas de la pieza" }),
  ).toHaveCount(0)
  assert.equal((await state(page)).drawingFile, "linked-drawing")
})

async function pointPosition(page, sample, cavity = "C13") {
  const point = page.getByRole("button", {
    name: `Consultar ${cavity} · ${sample}`,
    exact: true,
  })
  await point.scrollIntoViewIfNeeded()
  const bounds = await point.boundingBox()
  return { x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 }
}
async function hoverPoint(page, sample, cavity) {
  const position = await pointPosition(page, sample, cavity)
  await page.mouse.move(position.x, position.y)
  return position
}

async function correctionValue(page, sample, kind, change) {
  const detail = page.getByRole("region", { name: "Detalle del tramo" })
  const point = detail.getByRole("button", {
    name: `Consultar C13 · ${sample} · ${kind}`,
    exact: true,
  })
  await point.scrollIntoViewIfNeeded()
  const bounds = await point.boundingBox()
  await page.mouse.move(
    bounds.x + bounds.width / 2,
    bounds.y + bounds.height / 2,
  )
  await expect(
    detail
      .getByRole("tooltip")
      .getByText(`Variación: ${change} mm`, { exact: true })
      .first(),
  ).toBeVisible()
  await page.mouse.move(0, 0)
}

async function searchHeader(page, search) {
  const input = await search.boundingBox()
  const button = await page
    .getByRole("button", { name: "Plano", exact: true })
    .boundingBox()
  assert.ok(Math.abs(input.y - button.y) <= 1)
  assert.ok(Math.abs(input.height - button.height) <= 1)
  assert.ok(button.x > input.x + input.width)
  const scrollY = await page.evaluate(() => window.scrollY)
  return {
    input: { ...input, y: input.y + scrollY },
    button: { ...button, y: button.y + scrollY },
  }
}

test("part opens a single consultation with independent filters and no raw document sections", async (t) => {
  const page = await mount(t)
  await expect(
    page.getByRole("combobox", { name: "Buscar cota" }),
  ).toBeVisible()
  const header = await searchHeader(
    page,
    page.getByRole("combobox", { name: "Buscar cota" }),
  )
  const correctionButton = await page
    .getByRole("button", { name: "Correcciones", exact: true })
    .boundingBox()
  assert.equal(correctionButton.x, header.input.x)
  assert.ok(correctionButton.y > header.input.y + header.input.height)
  for (const label of ["Elemento", "Altura", "Evaluación"])
    await expect(
      page.getByRole("combobox", { name: label, exact: true }),
    ).toBeVisible()
  assert.equal(await page.getByRole("tab").count(), 0)
  assert.equal(await page.getByRole("table").count(), 0)
  assert.equal(await page.locator("aside").count(), 0)
  for (const text of [
    "Documentos",
    "Nubes de puntos y PUNTS_NOUS",
    "Perfiles A/B",
    "Acciones documentadas",
    "← Piezas",
    "Cotas y mediciones · revisión 06",
    "Banda de tolerancia",
    "Pasa el cursor o toca un muestreo para consultar sus valores.",
    "Incorporar mediciones",
    "Reimportar archivos",
  ])
    assert.equal(await page.getByText(text, { exact: true }).count(), 0)
  await choose(page, "Elemento", "B2")
  await choose(page, "Altura", "5,0 mm")
  await choose(page, "Evaluación", "LP máximo")
  const selected = await state(page)
  assert.equal(selected.element, "B2")
  assert.equal(String(selected.height), "5.0")
  assert.equal(String(selected.evaluation), "2")
  await page.screenshot({
    path: path.join(artifacts, "measurements-desktop.png"),
    fullPage: true,
  })
})

test("graph tooltips appear only at points, follow the point and contain only cavity values", async (t) => {
  const page = await mount(t)
  const sample = page.getByRole("button", {
    name: "Consultar C13 · intern.03",
    exact: true,
  })
  const position = await hoverPoint(page, "intern.03")
  const values = page.getByRole("tooltip")
  await expect(values).toBeVisible()
  await expect(values.getByText("3,976 mm", { exact: true })).toBeVisible()
  await expect(values.getByText("C16", { exact: true })).toBeVisible()
  assert.equal(await values.getByRole("link").count(), 0)
  assert.doesNotMatch(await values.innerText(), /Dentro|Fuera|Fuente|3,900/)
  let bounds = await values.boundingBox()
  assert.ok(bounds.x > position.x && bounds.x - position.x < 20)
  await page.mouse.move(position.x, position.y + 60)
  await expect(values).toHaveCount(0)
  const last = await hoverPoint(page, "intern.08")
  await expect(values.getByText("intern.08", { exact: true })).toBeVisible()
  bounds = await values.boundingBox()
  assert.ok(
    bounds.x + bounds.width < last.x && last.x - bounds.x - bounds.width < 20,
  )
  await page.getByRole("button", { name: "C16", exact: true }).click()
  await sample.focus()
  await expect(values).toBeVisible()
  assert.equal(await values.getByText("C16", { exact: true }).count(), 0)
  assert.equal(await page.getByRole("table").count(), 0)
  await page.screenshot({
    path: path.join(artifacts, "values-desktop.png"),
    fullPage: true,
  })
})

test("corrections preserve layout, evaluation and browser history, including the drawing", async (t) => {
  const page = await mount(t)
  await page.getByRole("combobox", { name: "Buscar cota" }).fill("170")
  await page.keyboard.press("Enter")
  await choose(page, "Elemento", "B2")
  await choose(page, "Altura", "5,0 mm")
  await choose(page, "Evaluación", "LP máximo")
  await page.getByRole("button", { name: "C16", exact: true }).click()
  const original = await state(page)
  const bounds = await page
    .getByRole("region", { name: "Evolución de mediciones" })
    .boundingBox()
  const documentTop = bounds.y + (await page.evaluate(() => window.scrollY))
  await page.getByRole("button", { name: "Correcciones", exact: true }).click()
  const comparison = page.getByRole("region", {
    name: "Evolución con correcciones",
  })
  await expect(comparison).toBeVisible()
  assert.equal((await state(page)).view, "correcciones")
  assert.equal(
    (await comparison.boundingBox()).y +
      (await page.evaluate(() => window.scrollY)),
    documentTop,
  )
  await expect(
    page.getByRole("combobox", { name: "Elemento", exact: true }),
  ).toHaveText("B2")
  await expect(
    page.getByRole("combobox", { name: "Evaluación", exact: true }),
  ).toHaveText("LP máximo")
  for (const sample of ["intern.01", "intern.03", "intern.05", "intern.08"]) {
    await expect(
      page.getByRole("button", {
        name: `Consultar C13 · ${sample}`,
        exact: true,
      }),
    ).toBeVisible()
  }
  await hoverPoint(page, "intern.08")
  await expect(
    page.getByRole("tooltip").getByText("intern.08", { exact: true }),
  ).toBeVisible()
  await page.mouse.move(0, 0)
  await correctionValue(page, "intern.03", "Predicción", "+0,500")
  await page
    .getByRole("region", { name: "Detalle del tramo" })
    .getByRole("button", { name: "C14", exact: true })
    .click()
  await expect(
    comparison.getByRole("button", { name: "C14", exact: true }),
  ).toHaveAttribute("aria-pressed", "false")
  const selectedCorrection = await state(page)
  await searchHeader(page, page.getByRole("combobox", { name: "Buscar cota" }))
  await page.screenshot({
    path: path.join(artifacts, "correction-desktop.png"),
    fullPage: true,
  })
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await expect(page.getByText("Plano · N170", { exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "DRW_3212.pdf",
  )
  const drawingQuery = page.getByRole("textbox", {
    name: "Buscar cota en el plano",
  })
  assert.equal(
    await page.evaluate(() => window.review.location().pathname),
    "/parts/part-one/fichero/drawing",
  )
  await expect(
    page.getByRole("region", { name: "Cotas de la pieza" }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toHaveCount(0)
  await drawingQuery.fill("N11")
  await expect(page.getByRole("status")).toHaveText("2 resultados")
  assert.equal((await state(page)).drawingQ, "N11")
  await page.evaluate(() => window.review.back())
  await expect(comparison).toBeVisible()
  assert.deepEqual(await state(page), selectedCorrection)
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toHaveAttribute("aria-pressed", "false")
  await page.evaluate(() => window.review.forward())
  await expect(drawingQuery).toHaveValue("N11")
  assert.equal(await page.getByRole("link", { name: /←|Volver/ }).count(), 0)
  await page.evaluate(() => window.review.back())
  await expect(comparison).toBeVisible()
  assert.deepEqual(await state(page), selectedCorrection)
  await page.evaluate(() => window.review.back())
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
  assert.deepEqual(await state(page), original)
  await page.evaluate(() => window.review.forward())
  await expect(comparison).toBeVisible()
})

test("search and corrections never substitute another cota or a local point for GLOBAL", async (t) => {
  const page = await mount(t, "/parts/part-one?tab=correcciones&caso=N165")
  await expect(
    page.getByRole("region", { name: "Evolución con correcciones" }),
  ).toBeVisible()
  await choose(page, "Elemento", "P01")
  await expect(
    page.getByText("Sin previsión documentada para esta evaluación."),
  ).toBeVisible()
  assert.equal(
    await page
      .getByRole("button", { name: /Consultar .*Previsión XLS/ })
      .count(),
    0,
  )
  await page.getByRole("combobox", { name: "Buscar cota" }).fill("240")
  await page.keyboard.press("Enter")
  assert.equal(
    await page.getByRole("combobox", { name: "Altura", exact: true }).count(),
    0,
  )
  assert.equal(
    await page.getByRole("combobox", { name: "Elemento", exact: true }).count(),
    0,
  )
  await expect(
    page.getByRole("button", { name: "Correcciones", exact: true }),
  ).toBeEnabled()
  await page.getByRole("combobox", { name: "Buscar cota" }).fill("288")
  await page.keyboard.press("Enter")
  await expect(page.getByRole("combobox", { name: "Buscar cota" })).toHaveValue(
    "N288",
  )
  await expect(
    page.getByText(/Esta cota no tiene mediciones incorporadas/),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toBeEnabled()
})

test("mobile layout and touch values remain within the viewport", async (t) => {
  const page = await mount(t, "/parts/part-one?cota=N170", true)
  const position = await pointPosition(page, "intern.03")
  await page.touchscreen.tap(position.x, position.y)
  await expect(
    page.getByRole("dialog", { name: "Valores de intern.03" }),
  ).toBeVisible()
  await page.screenshot({
    path: path.join(artifacts, "measurements-mobile.png"),
    fullPage: true,
  })
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await page
    .getByRole("heading", { name: "Evolución de mediciones", exact: true })
    .tap()
  await expect(
    page.getByRole("dialog", { name: "Valores de intern.03" }),
  ).toHaveCount(0)
  await page.getByRole("button", { name: "Correcciones", exact: true }).tap()
  await expect(
    page.getByRole("region", { name: "Evolución con correcciones" }),
  ).toBeVisible()
  const interval = page.getByRole("button", {
    name: "Tramo intern.03 a intern.05",
  })
  await interval.tap()
  await expect(interval).toHaveAttribute("aria-pressed", "true")
  await expect(
    page
      .getByRole("region", { name: "Detalle del tramo" })
      .getByText(/No hay una acción vinculada a N170/),
  ).toBeVisible()
  const current = await state(page)
  await page.getByRole("button", { name: "Plano", exact: true }).tap()
  await expect(
    page.getByRole("textbox", { name: "Buscar cota en el plano" }),
  ).toHaveValue("N170")
  await expect(
    page.getByRole("region", { name: "Cotas de la pieza" }),
  ).toHaveCount(0)
  await page.evaluate(() => window.review.back())
  await expect(interval).toHaveAttribute("aria-pressed", "true")
  assert.deepEqual(await state(page), current)
  await page.screenshot({
    path: path.join(artifacts, "correction-mobile.png"),
    fullPage: true,
  })
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
})

test("changing pieces clears the measurement and browser Back restores the previous consultation", async (t) => {
  const page = await mount(
    t,
    "/parts/part-one?feature=bolt-eye&cota=N170&view=correcciones&interval=03-05",
  )
  await expect(
    page.getByRole("region", { name: "Evolución con correcciones" }),
  ).toBeVisible()
  const previous = await state(page)
  await page.evaluate(() =>
    window.review.navigate({
      to: "/parts/$partId",
      params: { partId: "part-two" },
      search: { feature: "bolt-eye" },
    }),
  )
  await expect(
    page.getByRole("combobox", { name: "Buscar cota", exact: true }),
  ).toHaveValue("")
  assert.equal((await state(page)).cota, undefined)
  assert.equal((await state(page)).view, undefined)
  assert.equal((await state(page)).feature, "bolt-eye")
  await expect(
    page.getByRole("region", { name: "Evolución con correcciones" }),
  ).toHaveCount(0)
  await page.evaluate(() => window.review.back())
  await expect(
    page.getByRole("heading", { name: "Pump Housing", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Tramo intern.03 a intern.05" }),
  ).toHaveAttribute("aria-pressed", "true")
  assert.deepEqual(await state(page), previous)
})

test("legacy catalogue filters leave all piece cotas available and are cleared when opening the drawing", async (t) => {
  const page = await mount(t, "/parts/part-one?category=hole&tag=critical")
  const choices = page.getByRole("group", { name: "Cotas disponibles" })
  await expect(choices).toHaveCount(0)
  await page.getByRole("combobox", { name: "Buscar cota" }).fill("N")
  await expect(
    choices.getByRole("button", { name: "N240", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Más filtros", exact: true }),
  ).toHaveCount(0)
  await page.getByRole("option", { name: /^N170/ }).click()
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "DRW_3212.pdf", exact: true }),
  ).toBeVisible()
  assert.equal((await state(page)).category, undefined)
  assert.equal((await state(page)).tag, undefined)
  await page
    .getByRole("textbox", { name: "Buscar cota en el plano" })
    .fill("N113")
  await expect(page.getByRole("status")).toHaveText("2 resultados")
  await page.evaluate(() => window.review.back())
  await expect(page.getByRole("combobox", { name: "Buscar cota" })).toHaveValue(
    "N170",
  )
})

test("feature subcards only show their own cotas and do not repeat thumbnails", async (t) => {
  const page = await mount(t, "/parts/part-one?category=hole&tag=stiffness")
  const bolt = page.getByRole("region", {
    name: "Feature Bolt Eye",
    exact: true,
  })
  const seal = page.getByRole("region", { name: "Feature Seal", exact: true })
  await expect(
    bolt.getByRole("button", { name: "N170", exact: true }),
  ).toBeVisible()
  await expect(
    bolt.getByRole("button", { name: "N113", exact: true }),
  ).toHaveCount(0)
  await expect(
    seal.getByRole("button", { name: "N113", exact: true }),
  ).toBeVisible()
  await expect(bolt.getByRole("img")).toHaveCount(0)
  await expect(
    bolt.getByRole("link", { name: "Abrir Bolt Eye", exact: true }),
  ).toHaveAttribute("href", "/features/bolt-eye")
  await page.getByRole("combobox", { name: "Buscar cota" }).fill("N240")
  await expect(
    page
      .getByRole("group", { name: "Cotas disponibles" })
      .getByRole("button", { name: "N240", exact: true }),
  ).toBeVisible()
})

test("N170 describes the first proposal and keeps later intervals without inventing actions", async (t) => {
  const page = await mount(t, "/parts/part-one?cota=N170&view=correcciones")
  const detail = page.getByRole("region", { name: "Detalle del tramo" })
  const chart = page.getByRole("region", { name: "Evolución con correcciones" })
  await expect(
    chart.getByRole("group", { name: "Tramos entre muestreos" }),
  ).toBeVisible()
  assert.equal(await chart.getByRole("button", { name: /^Tramo / }).count(), 3)
  assert.equal(await detail.getByRole("img").count(), 1)
  assert.equal(await detail.getByRole("link").count(), 0)
  assert.equal(await detail.locator("details").count(), 0)
  assert.equal(
    await page.getByText("Documentos y valores de origen").count(),
    0,
  )
  await expect(detail.getByText(/expulsores de Ø4 mm/)).toBeVisible()
  await correctionValue(page, "intern.03", "Predicción", "+0,500")
  await correctionValue(page, "intern.03", "Cambio medido", "+0,547")
  assert.deepEqual(
    await detail.locator("svg text[y='263']").allTextContents(),
    ["intern.01", "intern.03"],
  )
  await page
    .getByRole("button", { name: "Tramo intern.03 a intern.05" })
    .click()
  await expect(
    detail.getByText("No hay una acción vinculada a N170."),
  ).toBeVisible()
  await expect(
    detail.getByText("Sin previsión documentada para esta evaluación."),
  ).toBeVisible()
  await correctionValue(page, "intern.05", "Cambio medido", "+0,001")
  await page
    .getByRole("button", { name: "Tramo intern.05 a intern.08" })
    .click()
  await expect(
    detail.getByText("No hay una acción vinculada a N170."),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Tramo intern.03 a intern.05" }),
  ).toHaveAttribute("aria-pressed", "false")
  assert.equal((await state(page)).interval, "05-08")
  const lastRegion = page.getByRole("button", {
    name: "Tramo intern.05 a intern.08",
  })
  const regionBounds = await lastRegion.boundingBox()
  const plotBounds = await chart.getByRole("img").boundingBox()
  assert.ok(regionBounds.x > plotBounds.x && regionBounds.y >= plotBounds.y)
  assert.ok(
    regionBounds.y + regionBounds.height < plotBounds.y + plotBounds.height,
  )
  await page.mouse.move(
    regionBounds.x + regionBounds.width / 2,
    regionBounds.y + 180,
  )
  await expect(page.getByRole("tooltip")).toHaveCount(0)
  const firstRegion = page.getByRole("button", {
    name: "Tramo intern.01 a intern.03",
  })
  await firstRegion.focus()
  await firstRegion.press("Enter")
  await expect(firstRegion).toHaveAttribute("aria-pressed", "true")
  await expect(detail.getByText(/expulsores de Ø4 mm/)).toBeVisible()
  await lastRegion.focus()
  await lastRegion.press("Space")
  await expect(lastRegion).toHaveAttribute("aria-pressed", "true")
  await hoverPoint(page, "intern.03")
  await expect(page.getByRole("tooltip")).toBeVisible()
  assert.equal((await state(page)).interval, "05-08")
  await page.mouse.move(0, 0)
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await page.evaluate(() => window.review.back())
  await expect(
    page.getByRole("button", { name: "Tramo intern.05 a intern.08" }),
  ).toHaveAttribute("aria-pressed", "true")
  assert.equal(await page.getByRole("table").count(), 0)
})

test("both documented plans of a cota are accessible without assigning unvalidated forecasts", async (t) => {
  const page = await mount(t, "/parts/part-one?cota=N161&view=correcciones")
  const detail = page.getByRole("region", { name: "Detalle del tramo" })
  await expect(
    page.getByRole("button", { name: "Tramo intern.03 a intern.05" }),
  ).toHaveAttribute("aria-pressed", "true")
  await expect(
    detail.getByText(/reducir 0,305 mm en diámetro total/),
  ).toBeVisible()
  await correctionValue(page, "intern.05", "Predicción", "−0,305")
  await correctionValue(page, "intern.05", "Cambio medido", "−0,335")
  await page
    .getByRole("button", { name: "Tramo intern.01 a intern.03" })
    .click()
  await expect(
    detail.getByText("Ajustar el diámetro interior según la zona marcada."),
  ).toBeVisible()
  await expect(
    detail.getByText("Sin previsión documentada para esta evaluación."),
  ).toBeVisible()
  await correctionValue(page, "intern.03", "Cambio medido", "−0,089")
})

test("unfinished numbers suggest cotas and the selected number stays only in the search", async (t) => {
  const page = await mount(t)
  const search = page.getByRole("combobox", { name: "Buscar cota" })
  await expect(search).toHaveValue("N170")
  for (const prefix of ["N1", "N11", "11", "n 11"]) {
    await search.fill(prefix)
    await expect(page.getByRole("option", { name: /^N113/ })).toBeVisible()
  }
  await page.getByRole("option", { name: /^N113/ }).click()
  await expect(search).toHaveValue("N113")
  assert.equal((await state(page)).cota, "N113")
  assert.equal(
    await page.getByText("N113 3+0.1 A 1", { exact: true }).count(),
    0,
  )
  assert.equal(await page.getByRole("heading", { name: /^N113/ }).count(), 0)
  await page.getByRole("button", { name: "Limpiar busqueda" }).click()
  await expect(search).toHaveValue("")
  await search.fill("N113")
  await page.keyboard.press("Enter")
  await expect(search).toHaveValue("N113")
})

for (const mobile of [false, true]) {
  test(`pinned measurements open their raw CSV and restore the consultation (${mobile ? "mobile" : "desktop"})`, async (t) => {
    const page = await mount(t, "/parts/part-one?cota=N170", mobile)
    const previous = await state(page)
    const position = await pointPosition(page, "intern.03")
    if (mobile) await page.touchscreen.tap(position.x, position.y)
    else await page.mouse.click(position.x, position.y)
    const dialog = page.getByRole("dialog", { name: "Valores de intern.03" })
    await expect(dialog).toBeVisible()
    await expect(
      dialog.getByRole("button", { name: /^Ver origen / }),
    ).toHaveCount(4)
    await page.mouse.move(0, 0)
    await expect(dialog).toBeVisible()
    await dialog
      .getByRole("button", { name: "Ver origen C13 · 3,976 mm", exact: true })
      .click()
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "measurement.csv",
    )
    const search = page.getByRole("textbox", { name: "Buscar en el archivo" })
    await expect(search).toHaveValue("Línea 2 · N170")
    await expect(page.locator("td[aria-current='true']")).toHaveText("3.976")
    await search.fill("3.977")
    await expect(page.locator("td[aria-current='true']")).toHaveText("3.977")
    await search.fill("inexistente")
    await expect(page.getByRole("status")).toHaveText("Sin resultados")
    await page
      .getByRole("button", { name: "Volver al origen de la medición" })
      .click()
    await expect(page.locator("td[aria-current='true']")).toHaveText("3.976")
    await page.screenshot({
      path: path.join(
        artifacts,
        `source-csv-${mobile ? "mobile" : "desktop"}.png`,
      ),
      fullPage: true,
    })
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    )
    await page.evaluate(() => window.review.back())
    await expect(
      page.getByRole("combobox", { name: "Buscar cota" }),
    ).toHaveValue("N170")
    assert.deepEqual(await state(page), previous)
    const point = page.getByRole("button", {
      name: "Consultar C13 · intern.03",
      exact: true,
    })
    await point.focus()
    await point.press("Enter")
    await expect(dialog).toBeVisible()
    await point.press("Escape")
    await expect(dialog).toHaveCount(0)
  })
}

test("Excel origin selects its sheet and cell beyond the first page", async (t) => {
  const page = await mount(t)
  await page.evaluate(async () => {
    window.review.study.catalog.entries.find(
      (e) => e.id === "N170",
    ).series[0].records.c13["03"].source = {
      file_id: "excel",
      path: "report.xlsx",
      locator: "DR_PAR!H90",
    }
    await window.review.refetchEvidence()
  })
  const position = await pointPosition(page, "intern.03")
  await page.mouse.click(position.x, position.y)
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Ver origen C13 · 3,976 mm" })
    .click()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "report.xlsx",
  )
  await expect(
    page.getByRole("textbox", { name: "Buscar en el archivo" }),
  ).toHaveValue("DR_PAR!H90")
  await expect(page.getByRole("tab", { name: "DR_PAR" })).toHaveAttribute(
    "aria-selected",
    "true",
  )
  await expect(page.locator("td[aria-current='true']")).toHaveAttribute(
    "title",
    "DR_PAR!H90",
  )
  await expect(page.locator("td[aria-current='true']")).toHaveText("3.976")
  await page.getByRole("tab", { name: "INTRO" }).click()
  await expect(
    page.getByRole("cell", { name: "Informe", exact: true }),
  ).toBeVisible()
  await page
    .getByRole("textbox", { name: "Buscar en el archivo" })
    .fill("3.976")
  await expect(page.getByRole("tab", { name: "DR_PAR" })).toHaveAttribute(
    "aria-selected",
    "true",
  )
  await page.screenshot({
    path: path.join(artifacts, "source-excel-desktop.png"),
    fullPage: true,
  })
})

test("source preview shows an unavailable original without attributing another file", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    window.review.tableError = "El original ha cambiado."
  })
  const position = await pointPosition(page, "intern.03")
  await page.mouse.click(position.x, position.y)
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Ver origen C13 · 3,976 mm" })
    .click()
  await expect(page.getByRole("alert")).toHaveText("El original ha cambiado.")
  await expect(page.getByRole("table")).toHaveCount(0)
})

test("a tooltip does not include distant cavities from the same sampling", async (t) => {
  const page = await mount(t, "/parts/part-one?cota=N170", false, true)
  await hoverPoint(page, "intern.03", "C13")
  const tooltip = page.getByRole("tooltip")
  await expect(tooltip.getByText("C13", { exact: true })).toBeVisible()
  assert.equal(await tooltip.getByText("C16", { exact: true }).count(), 0)
  await hoverPoint(page, "intern.03", "C16")
  await expect(tooltip.getByText("4,300 mm", { exact: true })).toBeVisible()
  assert.equal(await tooltip.getByText("C13", { exact: true }).count(), 0)
  const point = page.getByRole("button", {
    name: "Consultar C13 · intern.03",
    exact: true,
  })
  await point.focus()
  await expect(tooltip.getByText("C13", { exact: true })).toBeVisible()
  await point.press("Escape")
  await expect(tooltip).toHaveCount(0)
})

for (const mobile of [false, true]) {
  test(`drawing results appear above the full-width plan (${mobile ? "mobile" : "desktop"})`, async (t) => {
    const page = await mount(
      t,
      mobile
        ? "/parts/part-one?cota=N170&view=correcciones&interval=03-05"
        : "/parts/part-one?cota=N170",
      mobile,
    )
    await page.getByRole("button", { name: "Plano", exact: true }).click()
    const search = page.getByRole("textbox", {
      name: "Buscar cota en el plano",
    })
    await expect(search).toHaveValue("N170")
    const results = page.getByRole("group", {
      name: "Coincidencias en el plano",
    })
    await expect(page.getByRole("status")).toHaveText("3 resultados")
    for (const label of ["N170", "N170.5", "N170.3"])
      await expect(
        results.getByRole("button", { name: label, exact: true }),
      ).toBeVisible()
    assert.equal(await page.locator("aside").count(), 0)
    for (const text of [
      "Incluir subcotas",
      "Sin lectura",
      "Descargar original",
      "Número de esta ubicación",
      "Guardar revisión",
      "3 ubicaciones · plano 07",
    ]) {
      assert.equal(await page.getByText(text, { exact: true }).count(), 0)
    }
    const plan = page.getByRole("region", { name: "Plano de prueba" })
    const bounds = await plan.boundingBox()
    const resultBounds = await results.boundingBox()
    const searchBounds = await search.boundingBox()
    assert.ok(resultBounds.y + resultBounds.height <= bounds.y)
    assert.equal(searchBounds.x, bounds.x)
    assert.ok(Math.abs(searchBounds.width - bounds.width) <= 2)
    await results.getByRole("button", { name: "N170.5", exact: true }).click()
    await expect(plan).toHaveText("Plano · N170.5")
    assert.deepEqual(
      await page.evaluate(() => window.review.drawingFocus.box),
      [80, 100, 100, 120],
    )
    await results.getByRole("button", { name: "N170.3", exact: true }).click()
    await expect(plan).toHaveText("Plano · N170.3")
    assert.equal(await page.evaluate(() => window.review.drawingFocus.page), 2)
    await page.screenshot({
      path: path.join(
        artifacts,
        `drawing-${mobile ? "mobile" : "desktop"}.png`,
      ),
      fullPage: true,
    })
    await search.fill("N11")
    await expect(page.getByRole("status")).toHaveText("2 resultados")
    await results
      .getByRole("button", { name: "N113 · 2/2", exact: true })
      .click()
    assert.equal(
      await page.evaluate(() => window.review.drawingFocus.id),
      "113-copy",
    )
    await search.fill("999")
    await expect(page.getByRole("status")).toHaveText("0 resultados")
    assert.equal(await results.getByRole("button").count(), 0)
    await page.getByRole("button", { name: "Limpiar busqueda" }).click()
    await expect(search).toHaveValue("")
    await expect(results).toHaveCount(0)
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    await page.evaluate(() => window.review.back())
    await expect(
      page.getByRole("combobox", { name: "Buscar cota" }),
    ).toHaveValue("N170")
    if (mobile)
      await expect(
        page.getByRole("button", { name: "Tramo intern.03 a intern.05" }),
      ).toHaveAttribute("aria-pressed", "true")
  })
}
