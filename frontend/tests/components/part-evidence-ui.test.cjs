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

test("a single consultation can start with a feature and then choose its piece", async (t) => {
  const page = await mount(t, "/parts")
  await expect(page.getByRole("heading", { name: "Metrología" })).toBeVisible()
  await expect(
    page.getByRole("combobox", { name: "Buscar cota", exact: true }),
  ).toBeDisabled()
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toBeDisabled()
  await page.getByRole("combobox", { name: "Pieza", exact: true }).click()
  await expect(page.getByRole("option", { name: /3212/ })).toBeVisible()
  await expect(page.getByRole("option", { name: /9000/ })).toHaveCount(0)
  await page
    .getByRole("combobox", { name: "Buscar pieza", exact: true })
    .press("Escape")
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  const featureSearch = page.getByRole("combobox", {
    name: "Buscar feature",
    exact: true,
  })
  await featureSearch.fill("bolt")
  await featureSearch.press("Enter")
  await page.getByRole("combobox", { name: "Pieza", exact: true }).click()
  await expect(page.getByRole("option", { name: /3197/ })).toBeVisible()
  await expect(page.getByRole("option", { name: /9000/ })).toHaveCount(0)
  const pieceSearch = page.getByRole("combobox", {
    name: "Buscar pieza",
    exact: true,
  })
  await pieceSearch.fill("3212")
  await pieceSearch.press("Enter")
  await page.screenshot({
    path: path.join(artifacts, "metrology-feature-search.png"),
    fullPage: true,
  })
  await expect(
    page.getByRole("combobox", { name: "Pieza", exact: true }),
  ).toContainText("3212")
  await expect(page.getByRole("combobox", { name: "Buscar cota" })).toHaveValue(
    "",
  )
  assert.equal((await state(page)).feature, "bolt-eye")
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toHaveCount(0)
  const choices = page.getByRole("group", { name: "Cotas disponibles" })
  assert.deepEqual(await choices.getByRole("button").allTextContents(), [
    "N170",
    "N288",
  ])
  await choices.getByRole("button", { name: "N170", exact: true }).click()
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
  await expect(page.getByRole("status")).toHaveText("0 resultados")
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  assert.deepEqual(await state(page), selected)
  await page.evaluate(() => window.review.forward())
  await expect(
    page.getByRole("textbox", { name: "Buscar cota en el plano" }),
  ).toHaveValue("N113")
  await page.evaluate(() => window.review.back())
  assert.deepEqual(await state(page), selected)
  await choices.getByRole("button", { name: "N288", exact: true }).click()
  await expect(
    page.getByText(
      "Esta cota no tiene mediciones incorporadas. Puedes consultarla en el plano.",
    ),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toBeEnabled()
  await choose(page, "Feature", "Todos los features")
  await choices.getByRole("button", { name: "N240", exact: true }).click()
  await expect(
    page.getByRole("region", { name: "Evolución con correcciones" }),
  ).toBeVisible()
  assert.equal((await state(page)).feature, undefined)
  await choose(page, "Feature", "Rib")
  await expect(
    page.getByText(/todavía no tiene cotas vinculadas/),
  ).toBeVisible()
})

test("a piece starts without an arbitrary cota and includes unassigned cotas on mobile", async (t) => {
  const page = await mount(t, "/parts/part-one", true)
  const search = page.getByRole("combobox", { name: "Buscar cota" })
  await expect(search).toHaveValue("")
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toHaveCount(0)
  await page
    .getByRole("group", { name: "Cotas disponibles" })
    .getByRole("button", { name: "N240", exact: true })
    .click()
  await expect(search).toHaveValue("N240")
  await choose(page, "Feature", "Bolt Eye")
  await page.screenshot({
    path: path.join(artifacts, "metrology-feature-mobile.png"),
    fullPage: true,
  })
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  const filterSearch = page.getByRole("combobox", {
    name: "Buscar feature",
    exact: true,
  })
  await expect(filterSearch).toBeFocused()
  await filterSearch.fill("bolt")
  await page.screenshot({
    path: path.join(artifacts, "metrology-selector-mobile.png"),
    fullPage: true,
  })
  await filterSearch.press("Escape")
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await search.fill("N240")
  await page.keyboard.press("Enter")
  assert.equal((await state(page)).cota, undefined)
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toHaveCount(0)
})

test("identical numbers in another piece do not use an incompatible measurement revision", async (t) => {
  const page = await mount(
    t,
    "/parts/part-two?feature=bolt-eye&cota=N170&revision=04",
  )
  await expect(
    page.getByRole("combobox", { name: "Pieza", exact: true }),
  ).toContainText("3197")
  assert.equal((await state(page)).revision, "04")
  await expect(
    page.getByText(/No hay mediciones de esta cota para la revisión vinculada/),
  ).toBeVisible()
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toHaveCount(0)
  await choose(page, "Pieza", "Seleccionar pieza")
  await expect(
    page.getByRole("combobox", { name: "Buscar cota", exact: true }),
  ).toBeDisabled()
  await expect(page.getByRole("article")).toHaveCount(0)
})

test("a direct URL cannot show an unassigned cota within a feature", async (t) => {
  const page = await mount(t, "/parts/part-one?feature=bolt-eye&cota=N240")
  await expect(
    page.getByText("Esta cota no está vinculada a los filtros seleccionados."),
  ).toBeVisible()
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toHaveCount(0)
})

async function choose(page, label, value) {
  await page.getByRole("combobox", { name: label, exact: true }).click()
  await page.getByRole("option", { name: value, exact: true }).click()
}

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
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await expect(
    page.getByRole("region", { name: "Evolución de mediciones" }),
  ).toBeVisible()
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

async function searchHeader(page, search) {
  const input = await search.boundingBox()
  const button = await page
    .getByRole("button", { name: "Plano", exact: true })
    .boundingBox()
  assert.ok(Math.abs(input.y - button.y) <= 1)
  assert.ok(Math.abs(input.height - button.height) <= 1)
  assert.ok(button.x > input.x + input.width)
  return { input, button }
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
    "Actualizar datos",
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
  await page.getByRole("button", { name: "Correcciones", exact: true }).click()
  const comparison = page.getByRole("region", {
    name: "Evolución con correcciones",
  })
  await expect(comparison).toBeVisible()
  assert.equal((await state(page)).view, "correcciones")
  assert.equal((await comparison.boundingBox()).y, bounds.y)
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
  await expect(
    page
      .getByRole("region", { name: "Efecto previsto" })
      .getByText("+0,500 mm", { exact: true }),
  ).toBeVisible()
  await choose(page, "Cavidad", "C14")
  const selectedCorrection = await state(page)
  const header = await searchHeader(
    page,
    page.getByRole("combobox", { name: "Buscar cota" }),
  )
  await page.screenshot({
    path: path.join(artifacts, "correction-desktop.png"),
    fullPage: true,
  })
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await expect(page.getByText("Plano · N170", { exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Metrología")
  const drawingQuery = page.getByRole("textbox", {
    name: "Buscar cota en el plano",
  })
  assert.deepEqual(await searchHeader(page, drawingQuery), header)
  await expect(
    page.getByRole("button", { name: "Plano", exact: true }),
  ).toHaveAttribute("aria-pressed", "true")
  await drawingQuery.fill("N11")
  await expect(page.getByRole("status")).toHaveText("2 resultados")
  assert.equal((await state(page)).drawingQ, "N11")
  await page.getByRole("button", { name: "Plano", exact: true }).click()
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
  await expect(page.getByRole("tooltip")).toBeVisible()
  await page.screenshot({
    path: path.join(artifacts, "measurements-mobile.png"),
    fullPage: true,
  })
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await page.touchscreen.tap(position.x, position.y + 60)
  await expect(page.getByRole("tooltip")).toHaveCount(0)
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
      .getByText(/no hay una acción vinculada a N170/),
  ).toBeVisible()
  const current = await state(page)
  await page.getByRole("button", { name: "Plano", exact: true }).tap()
  await searchHeader(
    page,
    page.getByRole("textbox", { name: "Buscar cota en el plano" }),
  )
  await page.getByRole("button", { name: "Plano", exact: true }).tap()
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
  await page.getByRole("combobox", { name: "Pieza", exact: true }).click()
  await page.getByRole("option", { name: /3197/ }).click()
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
    page.getByRole("combobox", { name: "Pieza", exact: true }),
  ).toContainText("3212")
  await expect(
    page.getByRole("button", { name: "Tramo intern.03 a intern.05" }),
  ).toHaveAttribute("aria-pressed", "true")
  assert.deepEqual(await state(page), previous)
})

test("category and tag select linked cotas of matching features and persist in the drawing", async (t) => {
  const page = await mount(t, "/parts/part-one")
  const choices = page.getByRole("group", { name: "Cotas disponibles" })
  await expect(
    choices.getByRole("button", { name: "N240", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Más filtros", exact: true }).click()
  await choose(page, "Categoría", "Agujero")
  assert.deepEqual(await choices.getByRole("button").allTextContents(), [
    "N170",
    "N288",
    "N113",
  ])
  await choose(page, "Tag", "critical")
  assert.deepEqual(await choices.getByRole("button").allTextContents(), [
    "N170",
    "N288",
  ])
  await choices.getByRole("button", { name: "N170", exact: true }).click()
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  await expect(
    page.getByRole("combobox", { name: "Pieza", exact: true }),
  ).toContainText("3212")
  await expect(
    page.getByRole("combobox", { name: "Tag", exact: true }),
  ).toContainText("critical")
  await choose(page, "Tag", "Todos los tags")
  await page
    .getByRole("textbox", { name: "Buscar cota en el plano" })
    .fill("N113")
  await expect(page.getByRole("status")).toHaveText("2 resultados")
  await page.getByRole("button", { name: "Plano", exact: true }).click()
  assert.equal((await state(page)).category, "hole")
  assert.equal((await state(page)).tag, undefined)
  assert.equal((await state(page)).cota, undefined)
  await choose(page, "Categoría", "Todas las categorías")
  await expect(
    choices.getByRole("button", { name: "N240", exact: true }),
  ).toBeVisible()
})

test("filters never combine the category of one feature with the tag of another", async (t) => {
  const page = await mount(t, "/parts/part-one?category=hole&tag=stiffness")
  await expect(
    page.getByText("No hay cotas vinculadas a los features de estos filtros."),
  ).toBeVisible()
  await expect(
    page.getByRole("group", { name: "Cotas disponibles" }),
  ).toHaveCount(0)
})

test("N170 describes the first proposal and keeps later intervals without inventing actions", async (t) => {
  const page = await mount(t, "/parts/part-one?cota=N170&view=correcciones")
  const detail = page.getByRole("region", { name: "Detalle del tramo" })
  const chart = page.getByRole("region", { name: "Evolución con correcciones" })
  await expect(
    chart.getByRole("group", { name: "Tramos entre muestreos" }),
  ).toBeVisible()
  assert.equal(await chart.getByRole("button", { name: /^Tramo / }).count(), 3)
  assert.equal(await detail.getByRole("img").count(), 0)
  assert.equal(await detail.getByRole("link").count(), 0)
  assert.equal(await detail.locator("details").count(), 0)
  assert.equal(
    await page.getByText("Documentos y valores de origen").count(),
    0,
  )
  await expect(detail.getByText(/expulsores de Ø4 mm/)).toBeVisible()
  await expect(
    detail
      .getByRole("region", { name: "Efecto previsto" })
      .getByText("+0,500 mm", { exact: true }),
  ).toBeVisible()
  await expect(
    detail
      .getByRole("region", { name: "Cambio medido" })
      .getByText("+0,547 mm", { exact: true }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Tramo intern.03 a intern.05" })
    .click()
  await expect(
    detail.getByText(/Existe un plan.*no hay una acción vinculada a N170/),
  ).toBeVisible()
  await expect(
    detail.getByText("Sin previsión documentada para esta evaluación."),
  ).toBeVisible()
  await expect(
    detail
      .getByRole("region", { name: "Cambio medido" })
      .getByText("+0,001 mm", { exact: true }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Tramo intern.05 a intern.08" })
    .click()
  await expect(
    detail.getByText(/No hay una actuación documentada/),
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
  await expect(
    detail
      .getByRole("region", { name: "Efecto previsto" })
      .getByText("−0,305 mm", { exact: true }),
  ).toBeVisible()
  await expect(
    detail
      .getByRole("region", { name: "Cambio medido" })
      .getByText("−0,335 mm", { exact: true }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Tramo intern.01 a intern.03" })
    .click()
  await expect(
    detail.getByText("Ajustar el diámetro interior según la zona marcada."),
  ).toBeVisible()
  await expect(
    detail.getByText("Sin previsión documentada para esta evaluación."),
  ).toBeVisible()
  await expect(
    detail
      .getByRole("region", { name: "Cambio medido" })
      .getByText("−0,089 mm", { exact: true }),
  ).toBeVisible()
})

test("importing files is confined to management and requires an explicit click", async (t) => {
  const page = await mount(t, "/manage-test")
  const button = page.getByRole("button", { name: "Reimportar archivos" })
  await expect(button).toBeEnabled()
  assert.deepEqual(await page.evaluate(() => window.review.imports), [])
  await button.click()
  await expect(page.getByRole("status")).toHaveText(
    "Datos disponibles para consultar.",
  )
  assert.deepEqual(await page.evaluate(() => window.review.imports), [
    "part-one",
  ])
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
        ? "/parts/part-one?cota=N170&plano=true&view=correcciones&interval=03-05"
        : "/parts/part-one/fichero/drawing?cota=N170",
      mobile,
    )
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
    const { input: searchBounds, button: toggleBounds } = await searchHeader(
      page,
      search,
    )
    assert.ok(resultBounds.y + resultBounds.height <= bounds.y)
    assert.equal(searchBounds.x, bounds.x)
    assert.ok(
      Math.abs(toggleBounds.x + toggleBounds.width - bounds.x - bounds.width) <=
        2,
    )
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
    await page.getByRole("button", { name: "Plano", exact: true }).click()
    await expect(
      page.getByRole("combobox", { name: "Buscar cota" }),
    ).toHaveValue("N170")
    if (mobile)
      await expect(
        page.getByRole("button", { name: "Tramo intern.03 a intern.05" }),
      ).toHaveAttribute("aria-pressed", "true")
  })
}
