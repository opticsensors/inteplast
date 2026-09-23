const assert = require("node:assert/strict")
const path = require("node:path")
const { before, after, test } = require("node:test")
const esbuild = require("esbuild")
const { chromium } = require("playwright")
const { expect } = require("@playwright/test")

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

test("feature pieces contain their own cotas and leave documents on the piece page", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    const feature = window.review.feature
    feature.parts.push({ id: "part-two", code: "3197", name: "Pot" })
    window.review.characteristics = feature.parts.map((part, index) => ({
      id: `cota-${index}`,
      part_id: part.id,
      code: index ? "N200" : "N117",
      revision: "06",
    }))
    feature.assets = [
      {
        id: "drawing-one",
        part: feature.parts[0],
        kind: "drawing",
        name: "drawing.pdf",
        file: {
          id: "file-one",
          filename: "drawing.pdf",
          content_type: "application/pdf",
          size: 128,
        },
      },
    ]
  })
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  for (const [code, name] of [
    ["3212", "Pump Housing"],
    ["3197", "Pot"],
  ]) {
    const piece = page.getByRole("region", {
      name: `Pieza ${code}`,
      exact: true,
    })
    await piece
      .getByRole("button", { name: `${code} ${name}`, exact: true })
      .click()
  }
  for (const editing of [false, true]) {
    if (editing)
      await page
        .getByRole("button", { name: "Editar feature", exact: true })
        .click()
    for (const [code, ownCota, otherCota] of [
      ["3212", "N117", "N200"],
      ["3197", "N200", "N117"],
    ]) {
      const piece = page.getByRole("region", {
        name: `Pieza ${code}`,
        exact: true,
      })
      await expect(
        piece.getByRole("heading", { name: "Cotas", exact: true }),
      ).toBeVisible()
      await expect(
        piece.getByRole("link", { name: ownCota, exact: true }),
      ).toBeVisible()
      await expect(
        piece.getByRole("link", { name: otherCota, exact: true }),
      ).toHaveCount(0)
      await expect(
        piece.getByRole("link", { name: `Ver pieza ${code}`, exact: true }),
      ).toHaveAttribute(
        "href",
        new RegExp(`/parts/${code === "3212" ? "part-one" : "part-two"}`),
      )
    }
    await expect(
      page.getByRole("heading", { name: "Documentación" }),
    ).toHaveCount(0)
    await expect(
      page.getByRole("button", { name: "Añadir fichero", exact: true }),
    ).toHaveCount(0)
    await expect(page.getByText("drawing.pdf", { exact: true })).toHaveCount(0)
  }
  assert.equal(
    await page.evaluate(() => window.review.feature.assets[0].file.id),
    "file-one",
  )
})

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
      .and(page.locator('[data-sidebar="menu-button"]'))
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
    .getByRole("button", { name: /^Editar(?: feature)?$/, exact: true })
    .first()
    .click()
  await page.getByPlaceholder("Nombre del feature").fill("Bolt Eye revisado")
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
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
  await page
    .getByRole("button", { name: /^Editar(?: feature)?$/, exact: true })
    .click()
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
  await page
    .getByRole("button", { name: "Más acciones del feature", exact: true })
    .click()
  await page.getByRole("menuitem", { name: "Eliminar", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByText(/Se eliminará «Bolt Eye»/).waitFor()
  await dialog.getByRole("button", { name: "Cancelar", exact: true }).click()
  assert.equal(await page.evaluate(() => window.review.deleted), false)
  await page.evaluate(async () => {
    window.review.user.id = "another-user"
    await window.review.refreshUser()
  })
  await page
    .getByRole("button", { name: "Más acciones del feature", exact: true })
    .waitFor({ state: "detached" })
  assert.equal(
    await page
      .getByRole("button", { name: /^Editar(?: feature)?$/, exact: true })
      .count(),
    1,
  )
  await page.evaluate(async () => {
    window.review.user.is_superuser = true
    await window.review.refreshUser()
  })
  await page
    .getByRole("button", { name: "Más acciones del feature", exact: true })
    .click()
  await page.getByRole("menuitem", { name: "Eliminar", exact: true }).click()
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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
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
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  await page
    .getByRole("button", { name: "Añadir feature", exact: true })
    .click()
  await expect(
    page.getByRole("menuitem", { name: "Bolt Eye", exact: true }),
  ).toHaveCount(0)
  await page.keyboard.press("Escape")
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Discard")
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await readHeading(page, "Pump Housing")
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  await page.getByRole("button", { name: "Desvincular Bolt Eye" }).click()
  await page.getByText("Sin features vinculados.").waitFor()
  assert.equal(await page.evaluate(() => window.review.feature.parts.length), 0)
  await page
    .getByRole("button", { name: "Añadir feature", exact: true })
    .click()
  await page.getByRole("textbox", { name: "Buscar feature" }).fill("bolt")
  await page.getByRole("textbox", { name: "Buscar feature" }).press("ArrowDown")
  await expect(
    page.getByRole("menuitem", { name: "Bolt Eye", exact: true }),
  ).toBeFocused()
  await page.keyboard.press("Enter")
  await page.getByRole("link", { name: "Abrir Bolt Eye" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.parts[0].id),
    "part-one",
  )
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Pump Housing revisada")
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await readHeading(page, "Pump Housing revisada")
  await page.getByRole("link", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  await page
    .getByRole("link", { name: /3212.*Pump Housing revisada/ })
    .waitFor()
})

async function referencePiece(t) {
  const page = await mount(t)
  await page.evaluate(() => {
    window.review.parts[0].folder_path = "3212 Pump Housing"
    window.review.accessRequests = []
    window.review.partReferences = {
      "part-one": [
        {
          kind: "part",
          file: {
            id: "cad-original",
            filename: "original.step",
            size: 2048,
            content_type: "model/step",
          },
        },
        {
          kind: "drawing",
          file: {
            id: "drawing-original",
            filename: "DRW.pdf",
            size: 1024,
            content_type: "application/pdf",
          },
        },
      ],
    }
  })
  await page.getByRole("button", { name: "Abrir Pump Housing" }).click()
  await readHeading(page, "Pump Housing")
  await expect(
    page.getByRole("link", { name: "Descargar original.step", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  return page
}

test("reference changes stay in the draft, survive membership updates and cancel together", async (t) => {
  const page = await referencePiece(t)
  await expect(page.getByRole("link", { name: /^Descargar / })).toHaveCount(0)
  await expect(page.getByRole("group", { name: /^Archivo / })).toHaveCount(4)
  await expect(
    page.getByRole("button", { name: "Quitar Escaneo", exact: true }),
  ).toBeDisabled()
  let selectedPath = null
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: selectedPath } }),
  )
  await page.getByRole("button", { name: "Cambiar CAD", exact: true }).click()
  await expect(
    page.getByRole("link", { name: "CAD: original.step" }),
  ).toBeVisible()
  selectedPath = "Other/invalid.step"
  await page.getByRole("button", { name: "Cambiar CAD", exact: true }).click()
  await expect(page.getByRole("alert")).toHaveText(
    "Selecciona un archivo dentro de la carpeta de esta pieza.",
  )
  selectedPath = "3212 Pump Housing/replacement.step"
  await page.getByRole("button", { name: "Cambiar CAD", exact: true }).click()
  await expect(
    page.getByText("replacement.step", { exact: true }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Quitar Plano 2D", exact: true })
    .click()
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Draft name")
  await page.getByRole("button", { name: "Desvincular Bolt Eye" }).click()
  await expect(page.getByText("Sin features vinculados.")).toBeVisible()
  await expect(
    page.getByText("replacement.step", { exact: true }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(
      () => window.review.requests.filter((r) => r.kind === "part").length,
    ),
    0,
  )
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await readHeading(page, "Pump Housing")
  await expect(
    page.getByRole("link", { name: "Descargar original.step", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Descargar DRW.pdf", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  await expect(
    page.getByRole("link", { name: "CAD: original.step" }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Quitar Plano 2D", exact: true }),
  ).toBeEnabled()
})

test("reference save failure keeps the draft and retry saves header and files without refreshing data", async (t) => {
  const page = await referencePiece(t)
  let selectedPath = "3212 Pump Housing/replacement.step"
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: selectedPath } }),
  )
  await page.getByRole("button", { name: "Cambiar CAD", exact: true }).click()
  await expect(
    page.getByText("replacement.step", { exact: true }),
  ).toBeVisible()
  selectedPath = "3212 Pump Housing/scan.stl"
  await page
    .getByRole("button", { name: "Seleccionar Escaneo", exact: true })
    .click()
  await expect(page.getByText("scan.stl", { exact: true })).toBeVisible()
  await page
    .getByRole("button", { name: "Quitar Plano 2D", exact: true })
    .click()
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Updated piece")
  await page.evaluate(() => {
    window.review.failParts = true
  })
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click()
  await expect(page.getByRole("alert")).toHaveText(
    "No se pudo guardar la pieza",
  )
  await expect(
    page.getByText("replacement.step", { exact: true }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(
      () => window.review.partReferences["part-one"][0].file.filename,
    ),
    "original.step",
  )
  await page.evaluate(() => {
    window.review.failParts = false
    window.review.holdPartSave = true
  })
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click()
  await page.waitForFunction(() => Boolean(window.review.releasePartSave))
  await expect(
    page.getByRole("button", { name: "Cambiar CAD", exact: true }),
  ).toBeDisabled()
  await expect(
    page.getByRole("button", { name: "Cancelar", exact: true }),
  ).toBeDisabled()
  await page.evaluate(() => window.review.releasePartSave())
  await readHeading(page, "Updated piece")
  await expect(
    page.getByRole("link", { name: "Descargar replacement.step", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Descargar scan.stl", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Descargar DRW.pdf", exact: true }),
  ).toHaveCount(0)
  assert.deepEqual(
    await page.evaluate(() => window.review.refreshRequests ?? []),
    [],
  )
  assert.deepEqual(
    await page.evaluate(
      () =>
        window.review.requests.filter((r) => r.kind === "part").at(-1).patch,
    ),
    {
      name: "Updated piece",
      code: "3212",
      references: [
        {
          kind: "part",
          path: "3212 Pump Housing/replacement.step",
          source_version: null,
        },
        {
          kind: "scan",
          path: "3212 Pump Housing/scan.stl",
          source_version: null,
        },
        { kind: "drawing", path: null },
      ],
    },
  )
})

test("warning and lesson accordions reveal their text and stored images in consultation", async (t) => {
  const page = await mount(t)
  await page.route("**/api/v1/files/note-image?*", (route) =>
    route.fulfill({
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOioAAAAASUVORK5CYII=",
        "base64",
      ),
    }),
  )
  await page.evaluate(() => {
    window.review.accessRequests = []
    window.review.feature.notes = [
      {
        id: "warning-one",
        kind: "warning",
        title: "Revisar espesor",
        body: "Detalle del espesor\n\n![detalle.png](file:note-image)",
        position: 0,
      },
      {
        id: "lesson-one",
        kind: "lesson",
        title: "Ajustar el molde",
        body: "Resultado del ajuste",
        position: 0,
      },
    ]
  })
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  assert.equal(
    await page.getByText("Detalle del espesor", { exact: true }).count(),
    0,
  )
  await page
    .getByRole("button", { name: "Revisar espesor", exact: true })
    .click()
  await page.getByText("Detalle del espesor", { exact: true }).waitFor()
  await page.getByRole("img", { name: "detalle.png", exact: true }).waitFor()
  await page.waitForFunction(
    () => document.querySelector('img[alt="detalle.png"]')?.naturalWidth > 0,
  )
  await page
    .getByRole("button", { name: "Ajustar el molde", exact: true })
    .click()
  await page.getByText("Resultado del ajuste", { exact: true }).waitFor()
  await page
    .getByRole("button", { name: "Revisar espesor", exact: true })
    .click()
  assert.equal(
    await page.getByRole("img", { name: "detalle.png", exact: true }).count(),
    0,
  )
  assert.equal(
    await page.getByText("Resultado del ajuste", { exact: true }).isVisible(),
    true,
  )
})
