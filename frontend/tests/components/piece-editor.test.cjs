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
  "inteplast-piece-editor",
)
let browser, server, origin
before(async () => {
  const [{ createServer }, { default: tailwindcss }] = await Promise.all([
    import("vite"),
    import("@tailwindcss/vite"),
  ])
  fs.mkdirSync(artifacts, { recursive: true })
  server = await createServer({
    configFile: false,
    root: frontend,
    logLevel: "error",
    cacheDir: path.join(artifacts, "vite", String(process.pid)),
    optimizeDeps: { entries: [path.join(__dirname, "fixtures/catalog.jsx")] },
    esbuild: { jsx: "automatic" },
    resolve: {
      alias: [
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
        name: "piece-editor-fixture",
        configureServer(vite) {
          vite.middlewares.use("/piece-test", async (_req, res, next) => {
            try {
              const html = await vite.transformIndexHtml(
                "/piece-test",
                '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/tests/components/fixtures/catalog.jsx"></script></body></html>',
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
})
after(async () => {
  await browser?.close()
  await server?.close()
})

async function mount(t) {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
  })
  t.after(() => page.close())
  const errors = []
  page.on("pageerror", (error) => errors.push(error.message))
  t.after(() => assert.deepEqual(errors, []))
  await page.route("**/*", (route) =>
    route.request().url().startsWith(origin) ? route.continue() : route.abort(),
  )
  await page.goto(`${origin}/piece-test`)
  await page.getByRole("button", { name: "Nueva pieza", exact: true }).click()
  await expect(page.getByLabel("Nombre de la pieza")).toBeVisible()
  return page
}

async function choose(page, selected = "9001 New housing") {
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: selected } }),
  )
  await page
    .getByRole("button", { name: "Seleccionar carpeta", exact: true })
    .click()
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue(
    selected.split("/").pop(),
  )
  await page.getByLabel("Cliente", { exact: true }).fill("Example company")
}

test("new piece is an empty labelled page; folder proposals, arbitrary named files and features are drafts until creation", async (t) => {
  const page = await mount(t)
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue("")
  await expect(page.getByLabel("Código de la pieza")).toHaveValue("")
  await expect(page.getByLabel("Descripción (opcional)")).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Crear pieza", exact: true }),
  ).toBeDisabled()
  await expect(
    page.getByRole("button", { name: "Añadir fichero", exact: true }),
  ).toBeDisabled()
  await page.evaluate(() => {
    document.activeElement?.blur()
    window.scrollTo(0, 0)
  })
  await page.screenshot({
    path: path.join(artifacts, "new-empty-desktop.png"),
    fullPage: true,
  })
  await choose(page)
  await expect(page.getByLabel("Código de la pieza")).toHaveValue("9001")
  for (const name of ["part.step", "scan.stl", "mold.step", "drawing.pdf"])
    await expect(
      page.getByLabel(`Nombre de ${name}`, { exact: true }),
    ).toHaveValue(name)
  await page.getByLabel("Nombre de la pieza").fill("New Housing")
  await page
    .getByLabel("Descripción (opcional)")
    .fill("Pieza con varios ficheros de referencia")
  await page
    .getByRole("button", { name: "Añadir feature", exact: true })
    .click()
  await page.getByRole("textbox", { name: "Buscar feature" }).fill("bolt")
  await page.getByRole("menuitem", { name: "Bolt Eye", exact: true }).click()
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: "9001 New housing/alternative.step" } }),
  )
  await page
    .getByRole("button", { name: "Añadir fichero", exact: true })
    .click()
  await page
    .getByLabel("Nombre de alternative.step", { exact: true })
    .fill("CAD de revisión")
  await page
    .getByRole("button", { name: "Tipo de CAD de revisión: CAD", exact: true })
    .click()
  await page.getByRole("menuitem", { name: "Molde", exact: true }).click()
  await page
    .getByRole("button", {
      name: "Tipo de CAD de revisión: Molde",
      exact: true,
    })
    .click()
  await page.getByRole("menuitem", { name: "CAD", exact: true }).click()
  await page
    .getByRole("button", { name: "Usar CAD de revisión como principal" })
    .click()
  await expect(
    page.getByRole("button", { name: "Usar CAD de revisión como principal" }),
  ).toHaveAttribute("aria-pressed", "true")
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: "9001 New housing/sub/notes.txt" } }),
  )
  await page
    .getByRole("button", { name: "Añadir fichero", exact: true })
    .click()
  await page
    .getByLabel("Nombre de notes.txt", { exact: true })
    .fill("Notas del cliente")
  assert.equal(
    await page.evaluate(() => window.review.registrationRequests?.length ?? 0),
    0,
  )
  await expect(page.getByRole("link", { name: /^Descargar / })).toHaveCount(0)
  const addFile = await page
    .getByRole("button", { name: "Añadir fichero", exact: true })
    .getAttribute("class")
  const addFeature = await page
    .getByRole("button", { name: "Añadir feature", exact: true })
    .getAttribute("class")
  assert.equal(addFile, addFeature)
  await page.evaluate(() => {
    document.activeElement?.blur()
    window.scrollTo(0, 0)
  })
  await page.screenshot({
    path: path.join(artifacts, "new-populated-desktop.png"),
    fullPage: true,
  })
  await page.setViewportSize({ width: 390, height: 844 })
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  )
  await page.evaluate(() => {
    document.activeElement?.blur()
    window.scrollTo(0, 0)
  })
  await page.screenshot({
    path: path.join(artifacts, "new-populated-mobile.png"),
    fullPage: true,
  })
  await page.evaluate(() => {
    window.review.holdRefresh = true
  })
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "New Housing", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByText("Leyendo los datos de la carpeta…", { exact: true }),
  ).toBeVisible()
  await page.waitForFunction(() => Boolean(window.review.releaseRefresh))
  const registered = await page.evaluate(
    () => window.review.registrationRequests[0],
  )
  assert.equal(registered.files.length, 6)
  assert.equal(
    registered.files.find((file) => file.primary && file.kind === "part").name,
    "CAD de revisión",
  )
  assert.deepEqual(registered.feature_ids, ["feature-one"])
  await page.evaluate(() => window.review.releaseRefresh())
  await expect(
    page.getByText("Lectura completada", { exact: true }),
  ).toBeVisible()
  await page.getByText("Ficheros de la lectura (1)", { exact: true }).click()
  await expect(
    page.getByText("measurements.csv", { exact: true }),
  ).toBeVisible()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await page.setViewportSize({ width: 1440, height: 1050 })
  await page.evaluate(() => {
    document.activeElement?.blur()
    window.scrollTo(0, 0)
  })
  await page.screenshot({
    path: path.join(artifacts, "created-reading-result.png"),
    fullPage: true,
  })
  assert.equal(
    await page.evaluate(() => window.review.refreshRequests.length),
    1,
  )
  await page.evaluate(() => window.review.back())
  await expect(
    page.getByRole("heading", { name: "Catálogo", exact: true }),
  ).toBeVisible()
})

test("cancel, picker cancellation and duplicate folders do not register pieces", async (t) => {
  const page = await mount(t)
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: null } }),
  )
  await page
    .getByRole("button", { name: "Seleccionar carpeta", exact: true })
    .click()
  await expect(
    page.getByRole("button", { name: "Seleccionar carpeta", exact: true }),
  ).toBeEnabled()
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue("")
  await page.evaluate(() => {
    window.review.parts[0].folder_path = "3212 Pump Housing"
  })
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: "3212 Pump Housing" } }),
  )
  await page
    .getByRole("button", { name: "Seleccionar carpeta", exact: true })
    .click()
  await expect(
    page.getByRole("link", { name: "Abrir la pieza existente" }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Crear pieza", exact: true }),
  ).toBeDisabled()
  await choose(page)
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: "Elsewhere/file.txt" } }),
  )
  await page
    .getByRole("button", { name: "Añadir fichero", exact: true })
    .click()
  await expect(page.getByRole("alert")).toContainText("dentro de la carpeta")
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Catálogo", exact: true }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.registrationRequests?.length ?? 0),
    0,
  )
  await page.getByRole("button", { name: "Nueva pieza", exact: true }).click()
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue("")
})

test("a failed automatic read keeps the created piece and can retry without a second registration", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.evaluate(() => {
    window.review.failRead = true
  })
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "9001 New housing", exact: true }),
  ).toBeVisible()
  await expect(page.getByRole("alert")).toHaveText("No se pudo leer la carpeta")
  await page.evaluate(() => {
    window.review.failRead = false
  })
  await page
    .getByRole("button", { name: "Actualizar datos", exact: true })
    .click()
  await expect(
    page.getByText("Lectura completada", { exact: true }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.registrationRequests.length),
    1,
  )
  assert.equal(
    await page.evaluate(() => window.review.refreshRequests.length),
    2,
  )
})

test("leaving a dirty piece requests discard, and save failure keeps all editable fields", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page
    .getByRole("link", { name: "Catálogo", exact: true })
    .first()
    .click()
  await expect(
    page.getByRole("dialog", { name: "Cambios sin guardar" }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Seguir editando", exact: true })
    .click()
  await page.evaluate(() => {
    window.review.failRegistration = true
  })
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await expect(page.getByRole("alert")).toHaveText("No se pudo crear la pieza")
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue(
    "9001 New housing",
  )
  await expect(
    page.getByLabel("Nombre de part.step", { exact: true }),
  ).toHaveValue("part.step")
  await page
    .getByRole("link", { name: "Catálogo", exact: true })
    .first()
    .click()
  await page
    .getByRole("button", { name: "Descartar y salir", exact: true })
    .click()
  await expect(
    page.getByRole("heading", { name: "Catálogo", exact: true }),
  ).toBeVisible()
})

test("asynchronous correction progress is polled without starting another import", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.evaluate(() => {
    window.review.nextReadReport = {
      state: "processing",
      corrections_state: "queued",
      files: [
        { path: "corrections.pptx", group: "corrections", status: "queued" },
      ],
    }
  })
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await expect(
    page.getByText("Procesando las correcciones…", { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Actualizar datos", exact: true }),
  ).toBeDisabled()
  await page.evaluate(() => {
    const report = Object.values(window.review.readReports)[0]
    report.state = "ready"
    report.corrections_state = "ready"
    report.files[0].status = "used"
  })
  await expect(
    page.getByText("Lectura completada", { exact: true }),
  ).toBeVisible()
  await page.getByText("Ficheros de la lectura (1)", { exact: true }).click()
  await expect(
    page.getByText("corrections.pptx", { exact: true }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.refreshRequests.length),
    1,
  )
})
