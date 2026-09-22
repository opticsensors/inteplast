const assert = require("node:assert/strict")
const path = require("node:path")
const { before, after, test } = require("node:test")
const esbuild = require("esbuild")
const { chromium } = require("playwright")

const frontend = path.resolve(__dirname, "../..")
let browser
let bundle
before(async () => {
  const result = await esbuild.build({
    entryPoints: [path.join(__dirname, "fixtures/catalog.jsx")],
    bundle: true,
    write: false,
    format: "iife",
    platform: "browser",
    jsx: "automatic",
    loader: { ".svg": "dataurl" },
    tsconfig: path.join(frontend, "tsconfig.json"),
    define: { "process.env.NODE_ENV": '"development"' },
    plugins: [
      {
        name: "isolated-api",
        setup(build) {
          build.onResolve({ filter: /(?:^|\/)StepCoverCanvas$/ }, () => ({
            path: path.join(__dirname, "fixtures/cad-canvas.jsx"),
          }))
          build.onResolve({ filter: /^\.\/PdfViewer$/ }, () => ({
            path: path.join(__dirname, "fixtures/evidence-drawing.jsx"),
          }))
          build.onResolve({ filter: /^\/assets\// }, ({ path: asset }) => ({
            path: path.join(frontend, "public", asset),
          }))
          build.onResolve({ filter: /^@\/client$/ }, () => ({
            path: path.join(__dirname, "fixtures/api.js"),
          }))
        },
      },
    ],
  })
  bundle = result.outputFiles[0].text
  browser = await chromium.launch({ headless: true })
})
after(async () => browser?.close())

async function mount(t, initialPath = "/") {
  const page = await browser.newPage()
  page.on("pageerror", (error) => console.error(error.message))
  page.setDefaultTimeout(5000)
  t.after(() => page.close())
  await page.route("**/*", (route) =>
    route.request().url() === "http://component.invalid/"
      ? route.fulfill({
          contentType: "text/html",
          body: '<html><body><div id="root"></div></body></html>',
        })
      : route.abort(),
  )
  await page.goto("http://component.invalid/")
  await page.evaluate((value) => {
    window.catalogInitialPath = value
  }, initialPath)
  await page.addScriptTag({ content: bundle })
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).waitFor()
  return page
}

const readHeading = (page, name = "Bolt Eye") =>
  page.getByRole("heading", { name, exact: true }).waitFor()

test("shared searchable selectors keep Features filters and support keyboard and cancellation", async (t) => {
  const page = await mount(t)
  assert.equal(
    await page
      .getByRole("combobox", { name: "Categoría", exact: true })
      .count(),
    0,
  )
  const piece = page.getByRole("combobox", { name: "Pieza", exact: true })
  assert.equal(await piece.count(), 0)
  await page.getByRole("button", { name: "Filtros", exact: true }).click()
  await piece.click()
  const search = page.getByRole("combobox", {
    name: "Buscar pieza",
    exact: true,
  })
  await search.fill("pump")
  await search.press("Enter")
  assert.equal(
    await page.evaluate(() => window.review.location().search.part),
    "part-one",
  )
  await piece.click()
  await search.fill("no existe")
  await page.getByText("Sin coincidencias.", { exact: true }).waitFor()
  await search.press("Escape")
  assert.equal(await page.getByRole("dialog").count(), 0)
  assert.equal(
    await piece.evaluate((element) => element === document.activeElement),
    true,
  )
  assert.equal(
    await page.evaluate(() => window.review.location().search.part),
    "part-one",
  )
  await page.getByRole("combobox", { name: "Categoría", exact: true }).click()
  const category = page.getByRole("combobox", {
    name: "Buscar categoría",
    exact: true,
  })
  await category.press("ArrowDown")
  await category.press("Enter")
  assert.equal(
    await page.evaluate(() => window.review.location().search.category),
    "hole",
  )
  await page.getByRole("combobox", { name: "Tag", exact: true }).click()
  const tag = page.getByRole("combobox", { name: "Buscar tag", exact: true })
  await tag.fill("INYECC")
  await tag.press("Enter")
  assert.equal(
    await page.evaluate(() => window.review.location().search.tag),
    "inyeccion",
  )
  await page.getByRole("button", { name: "Filtros (3)", exact: true }).click()
  assert.equal(
    await page.getByRole("combobox", { name: "Tag", exact: true }).count(),
    0,
  )
  await page.getByRole("button", { name: "Filtros (3)", exact: true }).click()
  assert.match(
    await page.getByRole("combobox", { name: "Tag", exact: true }).innerText(),
    /inyeccion/,
  )
  await page.getByRole("button", { name: "Filtros (3)", exact: true }).click()
  await page
    .getByRole("button", { name: "Quitar filtro Tag: inyeccion", exact: true })
    .click()
  const remaining = await page.evaluate(() => window.review.location().search)
  assert.equal(remaining.tag, undefined)
  assert.equal(remaining.part, "part-one")
  assert.equal(remaining.category, "hole")
  await page.getByRole("button", { name: "Filtros (2)", exact: true }).waitFor()
  await page
    .getByRole("button", { name: "Limpiar filtros", exact: true })
    .click()
  const cleared = await page.evaluate(() => window.review.location().search)
  assert.equal(cleared.part, undefined)
  assert.equal(cleared.category, undefined)
  assert.equal(
    await page
      .getByRole("button", { name: "Limpiar filtros", exact: true })
      .count(),
    0,
  )
})

test("old home links preserve filters and cards open in read mode", async (t) => {
  const page = await mount(
    t,
    "/?q=3212&category=hole&tag=inyeccion&part=part-one&feature=feature-one",
  )
  const location = await page.evaluate(() => window.review.location())
  assert.equal(location.pathname, "/features")
  assert.equal(String(location.search.q), "3212")
  assert.equal(location.search.category, "hole")
  assert.equal(location.search.tag, "inyeccion")
  assert.equal(location.search.part, "part-one")
  assert.equal(location.search.feature, "feature-one")
  assert.equal(
    await page.getByRole("link", { name: "Dashboard", exact: true }).count(),
    0,
  )
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  assert.equal(await page.getByPlaceholder("Nombre del feature").count(), 0)
  assert.equal(
    await page
      .getByRole("link", { name: "Catálogo", exact: true })
      .getAttribute("data-active"),
    "true",
  )
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
  assert.equal(
    await page
      .getByPlaceholder("Buscar piezas, features o cotas…")
      .inputValue(),
    "3212",
  )
  await page.getByRole("button", { name: "Filtros (4)", exact: true }).waitFor()
  await page
    .getByRole("button", {
      name: "Quitar filtro Feature: Bolt Eye",
      exact: true,
    })
    .waitFor()
})

test("the searchable feature selector keeps the text search and sends an exact ID filter", async (t) => {
  const page = await mount(t, "/features?q=3212")
  await page.getByRole("button", { name: "Filtros", exact: true }).click()
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  const search = page.getByRole("combobox", {
    name: "Buscar feature",
    exact: true,
  })
  await search.fill("bolt")
  await search.press("Enter")
  await page.waitForFunction(() =>
    window.review.searchRequests.some(
      (params) => params.featureId === "feature-one" && params.q === "3212",
    ),
  )
  assert.equal(
    await page.evaluate(() => window.review.location().search.feature),
    "feature-one",
  )
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  await page
    .getByRole("option", { name: "Todos los features", exact: true })
    .click()
  assert.equal(
    await page.evaluate(() => window.review.location().search.feature),
    undefined,
  )
  assert.equal(
    await page
      .getByPlaceholder("Buscar piezas, features o cotas…")
      .inputValue(),
    "3212",
  )
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  await page.getByRole("option", { name: "Bolt Eye", exact: true }).click()
  await page.getByRole("button", { name: "Features", exact: true }).click()
  await page
    .getByRole("button", { name: "Limpiar filtros", exact: true })
    .click()
  const cleared = await page.evaluate(() => window.review.location().search)
  assert.equal(cleared.feature, undefined)
  assert.equal(String(cleared.q), "3212")
  assert.equal(cleared.kind, "feature")
  await page.getByRole("combobox", { name: "Feature", exact: true }).click()
  await page.getByRole("option", { name: "Bolt Eye", exact: true }).click()
  await page
    .getByRole("button", { name: "Limpiar busqueda", exact: true })
    .click()
  const textCleared = await page.evaluate(() => window.review.location().search)
  assert.equal(textCleared.q, undefined)
  assert.equal(textCleared.feature, "feature-one")
  assert.equal(textCleared.kind, "feature")
})

test("direct Edit saves into read mode and Back restores the search", async (t) => {
  const page = await mount(t)
  await page.getByPlaceholder("Buscar piezas, features o cotas…").fill("3212")
  await page
    .getByRole("button", { name: "Editar", exact: true })
    .first()
    .click()
  await page.getByPlaceholder("Nombre del feature").fill("Bolt Eye revisado")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await readHeading(page, "Bolt Eye revisado")
  assert.equal(
    await page.evaluate(() => window.review.location().search.editar),
    undefined,
  )
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
  assert.equal(
    await page
      .getByPlaceholder("Buscar piezas, features o cotas…")
      .inputValue(),
    "3212",
  )
})

test("Edit from a detail cancels into that detail without extra history", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  await page.getByRole("button", { name: "Editar", exact: true }).click()
  await page
    .getByPlaceholder("Nombre del feature")
    .fill("Descartar este cambio")
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await readHeading(page)
  assert.equal(
    await page.evaluate(() => window.review.feature.name),
    "Bolt Eye",
  )
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
})

test("deletion is secondary, confirmed, and only offered to owner or admin", async (t) => {
  const page = await mount(t)
  assert.equal(
    await page.getByRole("button", { name: "Eliminar", exact: true }).count(),
    0,
  )
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  await page.getByRole("button", { name: "Eliminar", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByText(/Se eliminará «Bolt Eye»/).waitFor()
  await dialog.getByRole("button", { name: "Cancelar", exact: true }).click()
  assert.equal(await page.evaluate(() => window.review.deleted), false)
  await page.evaluate(async () => {
    window.review.user.id = "another-user"
    await window.review.refreshUser()
  })
  await page
    .getByRole("button", { name: "Eliminar", exact: true })
    .waitFor({ state: "detached" })
  assert.equal(
    await page.getByRole("button", { name: "Editar", exact: true }).count(),
    1,
  )
  await page.evaluate(async () => {
    window.review.user.is_superuser = true
    await window.review.refreshUser()
  })
  await page.getByRole("button", { name: "Eliminar", exact: true }).click()
  await dialog.getByRole("button", { name: "Eliminar", exact: true }).click()
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
  await page.getByRole("button", { name: "Abrir Pump Housing" }).waitFor()
  assert.equal(
    await page.getByRole("button", { name: "Abrir Bolt Eye" }).count(),
    0,
  )
})

test("saving a new feature opens its completed detail and replaces the creation page in history", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Nuevo feature", exact: true }).click()
  await page.getByPlaceholder("Nombre del feature").fill("Nuevo nervio")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await readHeading(page, "Nuevo nervio")
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
})

test("the initial catalogue mixes cards, filters by type, and cotas appear only when searching", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Abrir Pump Housing" }).waitFor()
  assert.equal(
    await page.getByRole("region", { name: "Cotas encontradas" }).count(),
    0,
  )
  assert.equal(
    await page
      .getByRole("button", { name: "Nueva pieza", exact: true })
      .count(),
    1,
  )
  await page.getByRole("button", { name: "Features", exact: true }).click()
  await page
    .getByRole("button", { name: "Abrir Pump Housing" })
    .waitFor({ state: "detached" })
  await page.getByRole("button", { name: "Piezas", exact: true }).click()
  await page.getByRole("button", { name: "Abrir Pump Housing" }).waitFor()
  assert.equal(
    await page.getByRole("button", { name: "Abrir Bolt Eye" }).count(),
    0,
  )
  await page.getByRole("button", { name: "Todo", exact: true }).click()
  await page.getByPlaceholder("Buscar piezas, features o cotas…").fill("N170")
  await page
    .getByRole("region", { name: "Cotas encontradas" })
    .getByRole("link")
    .click()
  await readHeading(page, "Pump Housing")
  const location = await page.evaluate(() => window.review.location())
  assert.equal(location.pathname, "/parts/part-one")
  assert.equal(location.search.cota, "N170")
  assert.equal(location.search.revision, "06")
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
  assert.equal(
    await page
      .getByPlaceholder("Buscar piezas, features o cotas…")
      .inputValue(),
    "N170",
  )
})

test("piece editing saves and cancels header changes, and feature membership works in both directions", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Abrir Pump Housing" }).click()
  await readHeading(page, "Pump Housing")
  await page.getByRole("button", { name: "Editar", exact: true }).click()
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Discard")
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await readHeading(page, "Pump Housing")
  await page.getByRole("button", { name: "Editar", exact: true }).click()
  await page.getByRole("button", { name: "Desvincular Bolt Eye" }).click()
  await page.getByText("Sin features vinculados.").waitFor()
  assert.equal(await page.evaluate(() => window.review.feature.parts.length), 0)
  await page
    .getByRole("combobox", { name: "Añadir feature", exact: true })
    .click()
  await page.getByRole("option", { name: "Bolt Eye", exact: true }).click()
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.parts[0].id),
    "part-one",
  )
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Pump Housing revisada")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await readHeading(page, "Pump Housing revisada")
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  await page
    .getByRole("link", { name: /3212.*Pump Housing revisada/ })
    .waitFor()
})
