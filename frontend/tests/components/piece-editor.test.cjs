const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { before, after, test } = require("node:test")
const { chromium, expect } = require("@playwright/test")
const { warmUp } = require("./vite-warm-up.cjs")

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
    optimizeDeps: {
      entries: [path.join(__dirname, "fixtures/catalog.jsx")],
      // Loaded lazily with the graph view: declared so that Vite does not reload.
      include: ["force-graph"],
    },
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
  await warmUp(browser, `${origin}/piece-test`)
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
}

test("piece covers keep the feature carousel size in creation, consultation and editing", async (t) => {
  const page = await mount(t)
  const pieceCover = page
    .locator("main fieldset")
    .first()
    .locator(":scope > div")
    .first()
  await page.evaluate(() => {
    window.review.feature.parts.push({ id: "second-part", code: "9002" })
  })
  for (const [width, size] of [
    [1440, 300],
    [800, 300],
    [390, 192],
  ]) {
    await page.setViewportSize({ width, height: 950 })
    await page.evaluate(() => window.review.navigate({ to: "/parts/nueva" }))
    await expect(page.getByLabel("Código de la pieza")).toBeVisible()
    await expect(pieceCover).toHaveCSS("width", `${size}px`)
    await expect(pieceCover).toHaveCSS("height", `${size}px`)

    await page.evaluate(() =>
      window.review.navigate({
        to: "/parts/$partId",
        params: { partId: "part-one" },
      }),
    )
    const edit = page.getByRole("button", { name: "Editar pieza", exact: true })
    await expect(edit).toBeVisible()
    const before = await pieceCover.boundingBox()
    assert.equal(before.width, size)
    assert.equal(before.height, size)
    await edit.click()
    await expect(page.getByLabel("Código de la pieza")).toBeVisible()
    assert.deepEqual(await pieceCover.boundingBox(), before)

    await page.evaluate(() =>
      window.review.navigate({
        to: "/features/$featureId",
        params: { featureId: "feature-one" },
      }),
    )
    const carousel = page.getByRole("region", {
      name: "Capturas de las piezas",
    })
    await expect(carousel).toHaveCSS("width", `${size}px`)
    await expect(carousel).toHaveCSS("height", `${size}px`)
    await page
      .getByRole("button", { name: "Editar feature", exact: true })
      .click()
    await expect(
      page.getByRole("button", { name: "Cambiar imagen" }),
    ).toBeVisible()
    await expect(carousel).toHaveCSS("width", `${size}px`)
    await expect(carousel).toHaveCSS("height", `${size}px`)
  }
})

test("manual material and cavity count share the editor row and survive folder selection", async (t) => {
  const page = await mount(t)
  const material = page.getByRole("combobox", { name: "Material", exact: true })
  const cavities = page.getByRole("spinbutton", { name: "Nº de cavidades" })
  await material.click()
  await page.getByRole("button", { name: "Añadir material" }).click()
  const entry = page.getByRole("textbox", { name: "Añadir material" })
  await entry.fill("PA66 GF30")
  await entry.press("Enter")
  await expect(material).toHaveText("PA66 GF30")
  await cavities.fill("4")
  await choose(page)
  await expect(material).toHaveText("PA66 GF30")
  await expect(cavities).toHaveValue("4")
  const create = page.getByRole("button", { name: "Crear pieza", exact: true })
  await cavities.fill("0")
  await expect(create).toBeDisabled()
  await cavities.fill("4")
  await create.click()
  await expect(page.getByText("PA66 GF30", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  await expect(cavities).toHaveValue("4")
  const fields = [
    page.getByRole("combobox", { name: "Familia", exact: true }),
    page.getByRole("combobox", { name: "Cliente", exact: true }),
    material,
    cavities,
  ]
  const rects = await Promise.all(fields.map((field) => field.boundingBox()))
  for (let i = 1; i < rects.length; i++) {
    assert.ok(Math.abs(rects[i].y - rects[0].y) <= 1, JSON.stringify(rects))
    assert.ok(rects[i].x > rects[i - 1].x)
  }
  assert.ok(rects[3].width < rects[2].width)
  const header = page
    .locator("fieldset")
    .filter({ has: page.getByLabel("Código de la pieza") })
    .first()
  const cover = await header.locator(":scope > div").first().boundingBox()
  const description = await page.locator("#piece-description").boundingBox()
  assert.ok(Math.abs(cover.height - cover.width) <= 1)
  assert.ok(
    Math.abs(cover.y + cover.height - description.y - description.height) <= 1,
    JSON.stringify({ cover, description }),
  )
  await header.screenshot({
    path: path.join(artifacts, "material-cavities-header.png"),
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(cavities).toBeVisible()
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  )
})

test("a multi-component piece opens Componentes on creation and reads its data when closed", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.evaluate(() => {
    window.review.refreshRequests = []
  })
  await page
    .getByRole("checkbox", {
      name: "Varios componentes",
    })
    .check()
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  const dialog = page.getByRole("dialog", { name: "Componentes" })
  await expect(dialog).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.refreshRequests.length),
    0,
  )
  // Without components the piece is read as a single one.
  await dialog.getByRole("button", { name: "Cancelar" }).click()
  await expect(dialog).toHaveCount(0)
  await expect
    .poll(() => page.evaluate(() => window.review.refreshRequests.length))
    .toBe(1)
  assert.equal(
    await page.evaluate(() => window.review.location().search.componentes),
    undefined,
  )
  await page
    .getByRole("button", { name: "Actualizar datos", exact: true })
    .click()
  await expect
    .poll(() => page.evaluate(() => window.review.refreshRequests.length))
    .toBe(2)
})

test("components propose files and sheets by name; ambiguous or edited ones stay as chosen", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await page.evaluate(() => {
    window.review.componentExtraSources = [
      { path: "1- 2D y 3D pieza/20240508_BASE_RCP31.stp", kind: "part" },
      { path: "1- 2D y 3D pieza/Tapón_v2.pdf", kind: "drawing" },
      { path: "1- 2D y 3D pieza/BASE_TAPON conjunto.pdf", kind: "drawing" },
      { path: "1- 2D y 3D pieza/BASE2.pdf", kind: "drawing" },
      { path: "4- Metrologia/BASE informe.xls", kind: "measurements" },
    ]
    window.review.componentExtraSheets = ["DR(TAPÓN)", "Resumen base"]
  })
  await page.getByRole("button", { name: "Componentes", exact: true }).click()
  const dialog = page.getByRole("dialog", { name: "Componentes" })
  await dialog.getByRole("button", { name: "Añadir componente" }).click()
  await dialog.getByLabel("Nombre", { exact: true }).first().fill("BASE")
  await dialog.getByRole("button", { name: "Añadir componente" }).click()
  await dialog.getByLabel("Nombre", { exact: true }).nth(1).fill("Tapón")
  const owner = (label) => dialog.getByRole("combobox", { name: label })
  await expect(owner("Componente de base.pdf")).toHaveText("BASE")
  await expect(
    owner("Componente de 1- 2D y 3D pieza/20240508_BASE_RCP31.stp"),
  ).toHaveText("BASE")
  await expect(owner("Componente de 1- 2D y 3D pieza/Tapón_v2.pdf")).toHaveText(
    "Tapón",
  )
  // Two components, a different word or a whole workbook: no proposal.
  for (const path of [
    "1- 2D y 3D pieza/BASE_TAPON conjunto.pdf",
    "1- 2D y 3D pieza/BASE2.pdf",
    "4- Metrologia/BASE informe.xls",
    "cover.pdf",
  ])
    await expect(owner(`Componente de ${path}`)).toHaveText("Sin asignar")
  await expect(owner("Componente de la hoja DR(base)")).toHaveText("BASE")
  await expect(owner("Componente de la hoja DR(TAPÓN)")).toHaveText("Tapón")
  await expect(owner("Componente de la hoja Resumen base")).toHaveText("BASE")
  await expect(owner("Componente de la hoja DR(tapa)")).toHaveText(
    "Sin asignar",
  )
  // The user corrects a proposal and leaves another one unassigned.
  await owner("Componente de la hoja Resumen base").click()
  await page.getByRole("option", { name: "Sin asignar" }).click()
  await owner("Componente de cover.pdf").click()
  await page.getByRole("option", { name: "Tapón" }).click()
  await page.screenshot({
    path: path.join(artifacts, "component-proposals.png"),
    fullPage: true,
  })
  await dialog.getByRole("button", { name: "Guardar cambios" }).click()
  await expect(dialog).toHaveCount(0)
  const saved = await page.evaluate(() =>
    Object.values(window.review.organizations).at(-1),
  )
  const base = saved.find((c) => c.name === "BASE")
  const tapon = saved.find((c) => c.name === "Tapón")
  assert.equal(base.key, "BASE")
  assert.equal(tapon.key, "TAPON")
  assert.deepEqual(base.sheets.sort(), ["DR(base)"])
  assert.deepEqual(tapon.sheets, ["DR(TAPÓN)"])
  assert.deepEqual(base.files.map((f) => f.path).sort(), [
    "1- 2D y 3D pieza/20240508_BASE_RCP31.stp",
    "base.pdf",
  ])
  assert.deepEqual(tapon.files.map((f) => f.path).sort(), [
    "1- 2D y 3D pieza/Tapón_v2.pdf",
    "cover.pdf",
  ])
  assert.deepEqual(
    await page.evaluate(() =>
      Object.values(window.review.unassignedSources).at(-1),
    ),
    // Everything saved without component, touched or not (ambiguous, no match).
    [
      "file:1- 2D y 3D pieza/BASE2.pdf",
      "file:1- 2D y 3D pieza/BASE_TAPON conjunto.pdf",
      "file:4- Metrologia/BASE informe.xls",
      "sheet:DR(tapa)",
      "sheet:Resumen base",
    ],
  )
  // Saved choices, including leaving a sheet unassigned, are not proposed again.
  await page.getByRole("button", { name: "Componentes", exact: true }).click()
  await expect(owner("Componente de cover.pdf")).toHaveText("Tapón")
  await expect(owner("Componente de la hoja DR(base)")).toHaveText("BASE")
  await expect(owner("Componente de la hoja Resumen base")).toHaveText(
    "Sin asignar",
  )
  await expect(dialog.getByText("· Propuesta")).toHaveCount(0)
  await expect(
    dialog.getByRole("button", { name: "Guardar cambios" }),
  ).toBeDisabled()
  // Renaming Tapón to Tapa would resolve the ambiguous drawing and match DR(tapa):
  // both were saved unassigned, so they are not proposed.
  await dialog.getByLabel("Nombre", { exact: true }).nth(1).fill("Tapa")
  await expect(
    owner("Componente de 1- 2D y 3D pieza/BASE_TAPON conjunto.pdf"),
  ).toHaveText("Sin asignar")
  await expect(owner("Componente de la hoja DR(tapa)")).toHaveText(
    "Sin asignar",
  )
  await expect(dialog.getByText("· Propuesta")).toHaveCount(0)
  // A new file is proposed with the same rule; the saved ones stay as they are.
  await dialog.getByRole("button", { name: "Cancelar" }).click()
  await page.evaluate(() => {
    window.review.componentExtraSources.push({
      path: "1- 2D y 3D pieza/BASE rev 3.pdf",
      kind: "drawing",
    })
  })
  await page
    .getByRole("button", { name: "Actualizar datos", exact: true })
    .click()
  await page.getByRole("button", { name: "Componentes", exact: true }).click()
  await expect(
    owner("Componente de 1- 2D y 3D pieza/BASE rev 3.pdf"),
  ).toHaveText("BASE")
  await expect(dialog.getByText("· Propuesta")).toHaveCount(1)
  await dialog.getByRole("button", { name: "Cancelar" }).click()
})

test("component organization is optional and remembers sheet and drawing choices", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await page.evaluate(() => {
    window.review.componentExtraSources = [
      {
        path: "6- Método de medición/balloned/REV.01/BSG-296-01/BSG-296-01-N0 BASE SOP RCP 3.1_balloned.pdf",
        kind: "drawing",
      },
    ]
  })
  const organize = page.getByRole("button", {
    name: "Componentes",
    exact: true,
  })
  await organize.click()
  const dialog = page.getByRole("dialog", { name: "Componentes" })
  await dialog.getByRole("button", { name: "Usar propuesta" }).click()
  await expect(
    dialog.getByLabel("Nombre", { exact: true }).first(),
  ).toHaveValue("BASE")
  await expect(dialog.getByLabel("Nombre", { exact: true }).nth(1)).toHaveValue(
    "TAPA",
  )
  await dialog.getByRole("combobox", { name: "Componente de base.pdf" }).click()
  await page.getByRole("option", { name: "BASE", exact: true }).click()
  await dialog.getByLabel("Revisión de base.pdf").fill("01")
  await dialog
    .getByRole("combobox", { name: "Componente de cover.pdf" })
    .click()
  await page.getByRole("option", { name: "TAPA", exact: true }).click()
  await dialog.getByLabel("Revisión de cover.pdf").fill("02")
  await dialog.getByRole("button", { name: "Guardar cambios" }).click()
  await expect(dialog).toHaveCount(0)
  await organize.click()
  await expect(
    dialog.getByRole("combobox", { name: "Componente de la hoja DR(base)" }),
  ).toHaveText("BASE")
  await expect(
    dialog.getByRole("combobox", { name: "Componente de la hoja DR(tapa)" }),
  ).toHaveText("TAPA")
  await expect(dialog.getByLabel("Revisión de base.pdf")).toHaveValue("01")
  await expect(dialog.getByLabel("Revisión de cover.pdf")).toHaveValue("02")
  await dialog.getByLabel("Buscar archivo", { exact: true }).fill("cover")
  await expect(
    dialog.getByRole("combobox", { name: "Componente de base.pdf" }),
  ).toHaveCount(0)
  await expect(
    dialog.getByRole("combobox", { name: "Componente de cover.pdf" }),
  ).toBeVisible()
  await dialog.getByRole("button", { name: "Limpiar busqueda" }).click()
  await expect(dialog.getByLabel("Revisión de base.pdf")).toHaveValue("01")
  await page.screenshot({
    path: path.join(artifacts, "components.png"),
    fullPage: true,
  })
  await page.setViewportSize({ width: 390, height: 844 })
  assert.equal(
    await dialog.evaluate(
      (element) => element.scrollWidth <= element.clientWidth + 1,
    ),
    true,
  )
  await expect(
    dialog.getByRole("button", { name: "Cancelar", exact: true }),
  ).toBeVisible()
  await page.screenshot({
    path: path.join(artifacts, "components-mobile.png"),
    fullPage: true,
  })
})

test("with SharePoint the folder is chosen inside the application, without the Windows dialog", async (t) => {
  const page = await mount(t)
  let nativeRequests = 0
  await page.route("**/__native-picker", (route) => {
    nativeRequests += 1
    return route.fulfill({ json: { path: null } })
  })
  await page.evaluate(() => {
    window.review.sharepoint = true
    window.review.sourceFolders = ["9002 Shared housing"]
  })
  await page
    .getByRole("button", { name: "Seleccionar carpeta", exact: true })
    .click()
  const dialog = page.getByRole("dialog", { name: "Elegir carpeta" })
  const confirm = dialog.getByRole("button", { name: "Elegir esta carpeta" })
  await expect(confirm).toBeDisabled()
  await dialog
    .getByRole("button", { name: "9002 Shared housing", exact: true })
    .click()
  await expect(dialog.getByText("No hay subcarpetas.")).toBeVisible()
  await confirm.click()
  await expect(dialog).toHaveCount(0)
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue(
    "9002 Shared housing",
  )
  assert.equal(nativeRequests, 0)
  assert.deepEqual(
    await page.evaluate(() => window.review.sourceRequests.map((r) => r.path)),
    ["", "9002 Shared housing"],
  )
})

test("new piece is an empty labelled page; folder proposals, arbitrary named files and features are drafts until creation", async (t) => {
  const page = await mount(t)
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue("")
  await expect(page.getByLabel("Código de la pieza")).toHaveValue("")
  await expect(page.getByLabel("Descripción (opcional)")).toBeVisible()
  await page.getByLabel("Nombre de la pieza").fill("N".repeat(60))
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue(
    "N".repeat(45),
  )
  await page.getByLabel("Nombre de la pieza").fill("")
  await page.getByLabel("Descripción (opcional)").fill("D".repeat(210))
  await expect(page.getByLabel("Descripción (opcional)")).toHaveValue(
    "D".repeat(200),
  )
  await page.getByLabel("Descripción (opcional)").fill("")
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
    .getByRole("button", {
      name: "Tipo de CAD de revisión: CAD pieza",
      exact: true,
    })
    .click()
  await page.getByRole("menuitem", { name: "CAD molde", exact: true }).click()
  await page
    .getByRole("button", {
      name: "Tipo de CAD de revisión: CAD molde",
      exact: true,
    })
    .click()
  await page.getByRole("menuitem", { name: "CAD pieza", exact: true }).click()
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
    page.getByRole("heading", { name: "9001 New Housing", exact: true }),
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
    page.getByRole("button", { name: "Actualizar datos", exact: true }),
  ).toBeEnabled()
  await expect(
    page.getByRole("region", { name: "Lectura de datos" }),
  ).toHaveCount(0)
  await expect(page.getByText("measurements.csv", { exact: true })).toHaveCount(
    0,
  )
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
    page.getByRole("button", { name: "Actualizar datos", exact: true }),
  ).toBeEnabled()
  await expect(
    page.getByRole("region", { name: "Lectura de datos" }),
  ).toHaveCount(0)
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

test("changing an existing piece's folder keeps its edited name and code", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "9001 New housing", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  await page.getByLabel("Nombre de la pieza").fill("Custom part name")
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: "9002 Other housing" } }),
  )
  await page
    .getByRole("button", { name: "Cambiar carpeta de la pieza", exact: true })
    .click()
  await expect(
    page.getByText("9002 Other housing", { exact: true }),
  ).toBeVisible()
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue(
    "Custom part name",
  )
  await expect(page.getByLabel("Código de la pieza")).toHaveValue("9001")
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click()
  await expect(
    page.getByRole("heading", { name: "9001 Custom part name", exact: true }),
  ).toBeVisible()
  const saved = await page.evaluate(() =>
    window.review.requests.filter((request) => request.kind === "part"),
  )
  assert.equal(saved.length, 1)
  assert.equal(saved[0].patch.folder_path, "9002 Other housing")
  assert.equal(saved[0].patch.name, "Custom part name")
  assert.equal(saved[0].patch.code, "9001")
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
    report.state = "partial"
    report.corrections_state = "needs_review"
    report.files[0].status = "Pending interpretation"
  })
  await expect(
    page.getByRole("button", { name: "Actualizar datos", exact: true }),
  ).toBeEnabled()
  await expect(
    page.getByRole("region", { name: "Lectura de datos" }),
  ).toHaveCount(0)
  await expect(page.getByText("corrections.pptx", { exact: true })).toHaveCount(
    0,
  )
  // The report is retained, even though the piece view has no diagnostics panel.
  const report = await page.evaluate(
    () => Object.values(window.review.readReports)[0],
  )
  assert.equal(report.state, "partial")
  assert.equal(report.files[0].status, "Pending interpretation")
  assert.equal(
    await page.evaluate(() => window.review.refreshRequests.length),
    1,
  )
})

test("only an administrator deletes a piece, after reviewing its scope and typing its code", async (t) => {
  const page = await mount(t)
  await choose(page)
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  const more = page.getByRole("button", { name: "Más acciones de la pieza" })
  await expect(
    page.getByRole("button", { name: "Editar pieza", exact: true }),
  ).toBeVisible()
  await expect(more).toHaveCount(0)
  const partId = await page.evaluate(async () => {
    window.review.user.is_superuser = true
    await window.review.refreshUser()
    const part = window.review.parts.at(-1)
    window.review.deletionScopes = {
      [part.id]: {
        features: [{ id: "feature-one", name: "Bolt Eye" }],
        characteristics: 12,
        measurement_imports: 3,
        files_removed: 2,
        uploads_removed: 1,
        files_kept: 1,
        feature_assets: 4,
        key: "the-reviewed-scope",
      },
    }
    return part.id
  })
  await more.click()
  await page.getByRole("menuitem", { name: "Eliminar" }).click()
  const dialog = page.getByRole("dialog", { name: "Eliminar pieza" })
  const removed = dialog.getByRole("region", { name: "Se elimina" })
  await expect(removed.getByText("12 cotas")).toBeVisible()
  await expect(removed.getByText("3 mediciones importadas")).toBeVisible()
  await expect(
    removed.getByText("2 documentos vinculados (1 subido a la app)"),
  ).toBeVisible()
  await expect(removed.getByText("4 adjuntos de features")).toBeVisible()
  const kept = dialog.getByRole("region", { name: "Se conserva" })
  await expect(kept.getByText(/archivos y carpetas originales/)).toBeVisible()
  await expect(kept.getByText(/«Bolt Eye»/)).toBeVisible()
  const confirm = dialog.getByRole("button", { name: "Eliminar pieza" })
  await expect(confirm).toBeDisabled()
  await dialog.getByLabel(/Escribe el código/).fill("9000")
  await expect(confirm).toBeDisabled()
  await dialog.getByLabel(/Escribe el código/).fill("9001")
  await page.screenshot({ path: path.join(artifacts, "delete-piece.png") })
  await confirm.click()
  await expect(dialog).toHaveCount(0)
  assert.deepEqual(
    await page.evaluate(() => window.review.partDeleteConfirms),
    ["the-reviewed-scope"],
  )
  assert.equal(
    await page.evaluate(
      (id) => window.review.parts.some((part) => part.id === id),
      partId,
    ),
    false,
  )
  await expect
    .poll(() => page.evaluate(() => window.review.location().pathname))
    .toBe("/features")
})

test("a family added from the dropdown is shared with other pieces, which show the code first", async (t) => {
  const page = await mount(t)
  await choose(page)
  const family = page.getByRole("combobox", { name: "Familia", exact: true })
  await family.click()
  const search = page.getByRole("combobox", {
    name: "Buscar familia",
    exact: true,
  })
  // The last row adds one, like «Añadir pieza»: always there, even without text.
  const add = page.getByRole("button", { name: "Añadir familia", exact: true })
  await expect(add).toBeVisible()
  await expect(add.locator("svg")).toHaveCount(1)
  await page.screenshot({ path: path.join(artifacts, "family-dropdown.png") })
  // An existing name, with other case and spaces, selects it instead of duplicating.
  await add.click()
  const name = page.getByRole("textbox", {
    name: "Añadir familia",
    exact: true,
  })
  await expect(name).toBeFocused()
  await page.screenshot({ path: path.join(artifacts, "family-adding.png") })
  await name.fill("  pump   HOUSING ")
  await name.press("Enter")
  await expect(family).toHaveText("Pump Housing")
  assert.equal((await page.evaluate(() => window.review.families)).length, 1)
  // Escape cancels without adding anything.
  await family.click()
  await add.click()
  await name.fill("Descartada")
  await name.press("Escape")
  await expect(name).toHaveCount(0)
  await expect(add).toBeVisible()
  // The text already searched fills the new name.
  await search.fill("Tapa  roscada")
  await add.click()
  await expect(name).toHaveValue("Tapa roscada")
  await name.press("Enter")
  await expect(family).toHaveText("Tapa roscada")
  assert.ok(
    !(await page.evaluate(() => window.review.families)).some(
      (item) => item.name === "Descartada",
    ),
  )
  // The name is optional now; the customer is not required either.
  await page.getByLabel("Nombre de la pieza").fill("")
  await page.evaluate(() => {
    window.review.holdRefresh = false
  })
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "9001", exact: true }),
  ).toBeVisible()
  await expect(page.getByText("Tapa roscada", { exact: true })).toBeVisible()
  const registration = await page.evaluate(() =>
    window.review.registrationRequests.at(-1),
  )
  assert.equal(registration.name, null)
  assert.equal(registration.customer_id, null)
  const families = await page.evaluate(() => window.review.families)
  const added = families.find((item) => item.name === "Tapa roscada")
  assert.equal(registration.family_id, added.id)

  // The same family is offered to another piece, without adding it twice.
  await page.evaluate(() =>
    window.review.navigate({
      to: "/parts/$partId",
      params: { partId: "part-one" },
      search: { editar: true },
    }),
  )
  await expect(page.getByLabel("Código de la pieza")).toHaveValue("3212")
  await family.click()
  await search.fill("TAPA ROSCADA")
  await search.press("Enter")
  await expect(family).toHaveText("Tapa roscada")
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click()
  await expect(
    page.getByRole("heading", { name: "3212 Pump Housing", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByText("Tapa roscada · Bosch", { exact: true }),
  ).toBeVisible()
  const update = await page.evaluate(() =>
    window.review.requests.filter((request) => request.kind === "part").at(-1),
  )
  assert.equal(update.patch.family_id, added.id)
  assert.equal(
    (await page.evaluate(() => window.review.families)).filter(
      (item) => item.name === "Tapa roscada",
    ).length,
    1,
  )

  // Catalogue card: code as title, name beside it, then «Familia · Cliente».
  await page.evaluate(() =>
    window.review.navigate({ to: "/features", search: { kind: "part" } }),
  )
  const card = page
    .getByRole("button", { name: "Abrir 3212 Pump Housing" })
    .locator("..")
  await expect(card.getByRole("heading", { level: 3 })).toHaveText(
    "3212 Pump Housing",
  )
  await expect(
    card.getByText("Tapa roscada · Bosch", { exact: true }),
  ).toBeVisible()
  await expect(
    page
      .getByRole("button", { name: "Abrir 9001" })
      .locator("..")
      .getByText("Tapa roscada", { exact: true }),
  ).toBeVisible()
})

test("on a phone the identity fields are stacked without horizontal scroll", async (t) => {
  const page = await mount(t)
  await page.setViewportSize({ width: 390, height: 900 })
  const code = await page.getByLabel("Código de la pieza").boundingBox()
  const name = await page.getByLabel("Nombre de la pieza").boundingBox()
  const family = await page
    .getByRole("combobox", { name: "Familia", exact: true })
    .boundingBox()
  const customer = await page
    .getByRole("combobox", { name: "Cliente", exact: true })
    .boundingBox()
  assert.ok(code.y + code.height <= name.y, "Nombre goes below Código")
  assert.ok(Math.abs(code.x - name.x) < 2, "Código and Nombre are aligned")
  assert.ok(family.y + family.height <= customer.y, "Cliente below Familia")
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await page.screenshot({
    path: path.join(artifacts, "identity-mobile.png"),
    fullPage: true,
  })
})

test("dragging a graph node preserves its position and camera, and only the graph consumes its wheel", async (t) => {
  const page = await mount(t)
  await page.evaluate(() =>
    window.review.navigate({ to: "/features", search: {} }),
  )
  await page.getByRole("button", { name: "Grafo", exact: true }).click()
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-ready", "true")
  await page.addStyleTag({ content: "body { padding-bottom: 150vh }" })
  await graph.evaluate((el) => el.scrollIntoView({ block: "center" }))
  const start = await graph.evaluate((el) => {
    const g = el.catalogGraph
    g.zoom(1.6).centerAt(12, 4)
    const node = g.graphData().nodes.find((n) => n.kind === "part")
    const p = g.graph2ScreenCoords(node.x, node.y)
    const rect = el.getBoundingClientRect()
    const previousStop = g.onEngineStop()
    window.review.afterDrag = new Promise((resolve) =>
      g.onEngineStop(() => {
        previousStop()
        resolve()
      }),
    )
    return {
      x: rect.left + p.x,
      y: rect.top + p.y,
      id: node.id,
      center: g.centerAt(),
    }
  })
  await page.mouse.move(start.x, start.y)
  await expect(graph).toHaveCSS("cursor", "pointer")
  await page.mouse.down()
  await page.mouse.move(start.x + 80, start.y + 35, { steps: 10 })
  await page.mouse.up()
  await page.evaluate(() => window.review.afterDrag)
  const end = await graph.evaluate((el, id) => {
    const g = el.catalogGraph
    const n = g.graphData().nodes.find((n) => n.id === id)
    const point = g.graph2ScreenCoords(n.x, n.y),
      rect = el.getBoundingClientRect()
    return {
      x: rect.left + point.x,
      y: rect.top + point.y,
      zoom: g.zoom(),
      center: g.centerAt(),
    }
  }, start.id)
  assert.equal(end.zoom, 1.6)
  assert.deepEqual(end.center, start.center)
  assert.ok(
    Math.abs(end.x - start.x - 80) < 2 && Math.abs(end.y - start.y - 35) < 2,
  )

  const scroll = () => page.evaluate(() => scrollY)
  const before = await scroll()
  await page.mouse.wheel(0, -80)
  await expect
    .poll(() => graph.evaluate((el) => el.catalogGraph.zoom()))
    .toBeGreaterThan(1.6)
  await graph.evaluate((el) => el.catalogGraph.zoom(el.catalogGraph.maxZoom()))
  await page.mouse.wheel(0, -400)
  await graph.evaluate((el) => el.catalogGraph.zoom(el.catalogGraph.minZoom()))
  await page.mouse.wheel(0, 400)
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  )
  assert.equal(await scroll(), before)
  const bounds = await graph.boundingBox()
  await page.mouse.move(
    bounds.x + bounds.width / 2,
    bounds.y + bounds.height + 8,
  )
  await page.mouse.wheel(0, 240)
  await expect.poll(scroll).toBeGreaterThan(before)
})

test("the graph can be used while a saved thumbnail is being checked", async (t) => {
  const page = await mount(t)
  await page.evaluate(async () => {
    const { CatalogService } = await import("/tests/components/fixtures/api.js")
    const image = {
      id: "graph-image",
      filename: "stored.png",
      content_type: "image/png",
    }
    window.review.parts[0].image = image
    CatalogService.readPartCover = async () => {
      await new Promise((resolve) => {
        window.review.releaseGraphCover = resolve
      })
      return { image }
    }
    const draw = CanvasRenderingContext2D.prototype.drawImage
    CanvasRenderingContext2D.prototype.drawImage = function (image, ...args) {
      if (
        image instanceof HTMLImageElement &&
        image.src.includes("graph-image")
      )
        window.review.paintedGraphCover = true
      return draw.call(this, image, ...args)
    }
    await window.review.navigate({ to: "/features", search: {} })
  })
  await page.route("**/files/graph-image?*", (route) =>
    route.fulfill({
      contentType: "image/svg+xml",
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="red"/></svg>',
    }),
  )
  await page.getByRole("button", { name: "Grafo", exact: true }).click()
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-ready", "true")
  await page.waitForFunction(
    () => typeof window.review.releaseGraphCover === "function",
  )
  await graph.evaluate((el) => el.catalogGraph.zoom(2))
  await page.evaluate(() => window.review.releaseGraphCover())
  await page.waitForFunction(() => window.review.paintedGraphCover)
  assert.equal(await graph.evaluate((el) => el.catalogGraph.zoom()), 2)
})

test("the catalogue graph is drawn with the theme colours, light and dark", async (t) => {
  const page = await mount(t)
  await page.evaluate(() =>
    window.review.navigate({ to: "/features", search: {} }),
  )
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Grafo" })
    .click()
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-ready", "true")
  await page.getByRole("checkbox", { name: "Familias" }).click()
  await page.getByRole("checkbox", { name: "Clientes" }).click()
  await expect(graph).toHaveAttribute("data-nodes", "4")
  await expect(graph).toHaveAttribute("data-ready", "true")
  // The canvas has a fixed pixel width: it must never widen the page.
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  const light = await graph.getAttribute("data-background")
  await page.screenshot({ path: path.join(artifacts, "graph-light.png") })
  await page.evaluate(() => document.documentElement.classList.add("dark"))
  await expect(graph).not.toHaveAttribute("data-background", light)
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(artifacts, "graph-dark.png") })
  assert.equal((await page.locator("canvas").count()) > 0, true)
})

test("grid and drawings views fit the page, on desktop and phone", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    const part = window.review.parts[0]
    window.review.drawings = ["base.pdf", "tapa.pdf", "conjunto.pdf"].map(
      (name, index) => ({
        file: { id: `drawing-${index}`, filename: name, version: "v1" },
        name,
        primary: index === 0,
        part,
        component: index === 0 ? "BASE" : null,
        revision: index === 0 ? "07" : null,
      }),
    )
    window.review.navigate({ to: "/features", search: {} })
  })
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Cuadrícula" })
    .click()
  await expect(page.locator("[data-view=grid]")).toBeVisible()
  const fits = () =>
    page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    )
  assert.ok(await fits())
  await page.screenshot({ path: path.join(artifacts, "catalog-grid.png") })
  await page.getByRole("button", { name: "Planos", exact: true }).click()
  await expect(page.locator("[data-view=drawings]")).toBeVisible()
  assert.ok(await fits())
  await page.screenshot({ path: path.join(artifacts, "catalog-drawings.png") })
  await page.setViewportSize({ width: 390, height: 900 })
  assert.ok(await fits())
  await page.screenshot({
    path: path.join(artifacts, "catalog-drawings-mobile.png"),
    fullPage: true,
  })
})

test("a feature suggested by the folder can be kept or removed before creating the piece", async (t) => {
  const page = await mount(t)
  await choose(page, "0- Bolt Eye/9001 New housing")
  const suggestion = page.getByRole("button", {
    name: "Desvincular Bolt Eye",
    exact: true,
  })
  await expect(suggestion).toBeVisible()
  // Removed before creating: the piece is created without it.
  await suggestion.click()
  await expect(suggestion).toHaveCount(0)
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await page.waitForFunction(
    () => window.review.registrationRequests?.length === 1,
  )
  const removed = await page.evaluate(
    () => window.review.registrationRequests[0],
  )
  assert.deepEqual(removed.feature_ids, [])
})

test("a kept folder suggestion is saved exactly as selected", async (t) => {
  const page = await mount(t)
  await choose(page, "0- Bolt Eye/9002 Other housing")
  await expect(
    page.getByRole("button", { name: "Desvincular Bolt Eye", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await page.waitForFunction(
    () => window.review.registrationRequests?.length === 1,
  )
  const kept = await page.evaluate(() => window.review.registrationRequests[0])
  assert.deepEqual(kept.feature_ids, ["feature-one"])
})

test("a feature added by hand survives a folder that suggests it and another that does not", async (t) => {
  const page = await mount(t)
  // Chosen by hand before any folder.
  await page
    .getByRole("button", { name: "Añadir feature", exact: true })
    .click()
  await page.getByRole("menuitem", { name: "Bolt Eye", exact: true }).click()
  const linked = page.getByRole("button", {
    name: "Desvincular Bolt Eye",
    exact: true,
  })
  await expect(linked).toBeVisible()
  // A folder that suggests it too, then one that suggests nothing.
  await choose(page, "0- Bolt Eye/9001 New housing")
  await expect(linked).toHaveCount(1)
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: "9002 Other housing" } }),
  )
  await page
    .getByRole("button", { name: "Cambiar carpeta de la pieza", exact: true })
    .click()
  await expect(page.getByLabel("Nombre de la pieza")).toHaveValue(
    "9002 Other housing",
  )
  await expect(linked).toHaveCount(1)
  await page.getByRole("button", { name: "Crear pieza", exact: true }).click()
  await page.waitForFunction(
    () => window.review.registrationRequests?.length === 1,
  )
  const request = await page.evaluate(
    () => window.review.registrationRequests[0],
  )
  assert.deepEqual(request.feature_ids, ["feature-one"])
  assert.equal(request.folder_path, "9002 Other housing")
  // Saved and reopened: the piece is still linked to it.
  const partId = await page.evaluate(() => window.review.parts.at(-1).id)
  await page.evaluate(() =>
    window.review.navigate({ to: "/features", search: { kind: "part" } }),
  )
  await page.evaluate(
    (id) =>
      window.review.navigate({ to: "/parts/$partId", params: { partId: id } }),
    partId,
  )
  await expect(
    page.getByRole("link", { name: "Abrir Bolt Eye", exact: true }),
  ).toBeVisible()
})
