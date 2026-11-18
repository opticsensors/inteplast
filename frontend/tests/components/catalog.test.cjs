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

test("shared searchable selectors filter by piece, feature, family and customer, with keyboard and cancellation", async (t) => {
  const page = await mount(t)
  const piece = page.getByRole("combobox", { name: "Pieza", exact: true })
  assert.equal(await piece.count(), 0)
  await page.getByRole("button", { name: "Filtros", exact: true }).click()
  // Category and tag were removed on 17/11/2026.
  for (const name of ["Categoría", "Tag"])
    assert.equal(
      await page.getByRole("combobox", { name, exact: true }).count(),
      0,
    )
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
  await page.getByRole("combobox", { name: "Familia", exact: true }).click()
  const family = page.getByRole("combobox", {
    name: "Buscar familia",
    exact: true,
  })
  await family.fill("PUMP")
  await family.press("Enter")
  assert.equal(
    await page.evaluate(() => window.review.location().search.family),
    "family-pump",
  )
  // Filters choose existing values; adding new ones belongs to the piece editor.
  await page.getByRole("combobox", { name: "Cliente", exact: true }).click()
  const customer = page.getByRole("combobox", {
    name: "Buscar cliente",
    exact: true,
  })
  await customer.fill("Otra empresa")
  await expect(
    page
      .getByRole("dialog", { name: "Selector de cliente" })
      .getByRole("button", { name: /Añadir/ }),
  ).toHaveCount(0)
  await customer.fill("")
  await customer.press("ArrowDown")
  await customer.press("Enter")
  assert.equal(
    await page.evaluate(() => window.review.location().search.customer),
    "customer-bosch",
  )
  await page.waitForFunction(() =>
    window.review.catalogRequests?.some(
      (params) =>
        params.familyId === "family-pump" &&
        params.customerId === "customer-bosch" &&
        params.partId === "part-one",
    ),
  )
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).waitFor()
  await page.getByRole("button", { name: "Filtros (3)", exact: true }).click()
  assert.equal(
    await page.getByRole("combobox", { name: "Cliente", exact: true }).count(),
    0,
  )
  await page.getByRole("button", { name: "Filtros (3)", exact: true }).click()
  assert.match(
    await page
      .getByRole("combobox", { name: "Cliente", exact: true })
      .innerText(),
    /Bosch/,
  )
  await page.getByRole("button", { name: "Filtros (3)", exact: true }).click()
  await page
    .getByRole("button", { name: "Quitar filtro Cliente: Bosch", exact: true })
    .click()
  const remaining = await page.evaluate(() => window.review.location().search)
  assert.equal(remaining.customer, undefined)
  assert.equal(remaining.part, "part-one")
  assert.equal(remaining.family, "family-pump")
  await page.getByRole("button", { name: "Filtros (2)", exact: true }).waitFor()
  await page
    .getByRole("button", { name: "Limpiar filtros", exact: true })
    .click()
  const cleared = await page.evaluate(() => window.review.location().search)
  assert.equal(cleared.part, undefined)
  assert.equal(cleared.family, undefined)
  assert.equal(
    await page
      .getByRole("button", { name: "Limpiar filtros", exact: true })
      .count(),
    0,
  )
})

test("a family and customer filter hides pieces that do not meet both", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    window.review.parts.push({
      id: "part-two",
      code: "3197",
      name: "Pot",
      family_id: "family-pot",
      customer_id: "customer-bosch",
      characteristic_count: 0,
    })
    window.review.families.push({ id: "family-pot", name: "Pot" })
  })
  await page.evaluate(() =>
    window.review.navigate({
      to: "/features",
      search: { kind: "part", customer: "customer-bosch" },
    }),
  )
  await page.getByRole("button", { name: "Abrir 3197 Pot" }).waitFor()
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).waitFor()
  await page.evaluate(() =>
    window.review.navigate({
      to: "/features",
      search: {
        kind: "part",
        customer: "customer-bosch",
        family: "family-pot",
      },
    }),
  )
  await page.getByRole("button", { name: "Abrir 3197 Pot" }).waitFor()
  await expect(
    page.getByRole("button", { name: "Abrir 3212 Pump Housing" }),
  ).toHaveCount(0)
})

test("old home links preserve filters and cards open in read mode", async (t) => {
  const page = await mount(
    t,
    "/?q=3212&category=hole&tag=inyeccion&part=part-one&feature=feature-one",
  )
  const location = await page.evaluate(() => window.review.location())
  assert.equal(location.pathname, "/features")
  assert.equal(String(location.search.q), "3212")
  // Category and tag no longer exist: old links open the same, ignoring them.
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
  await page.getByRole("button", { name: "Filtros (2)", exact: true }).waitFor()
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
  // Pieces sort by code, so the feature card is not the first one any more.
  await page
    .getByRole("button", { name: "Abrir Bolt Eye" })
    .locator("..")
    .getByRole("button", { name: /^Editar(?: feature)?$/, exact: true })
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
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).waitFor()
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
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).waitFor()
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
    .getByRole("button", { name: "Abrir 3212 Pump Housing" })
    .waitFor({ state: "detached" })
  await page.getByRole("button", { name: "Piezas", exact: true }).click()
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).waitFor()
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
  await readHeading(page, "3212 Pump Housing")
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
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).click()
  await readHeading(page, "3212 Pump Housing")
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
  await readHeading(page, "3212 Pump Housing")
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
  await readHeading(page, "3212 Pump Housing revisada")
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
  await page.getByRole("button", { name: "Abrir 3212 Pump Housing" }).click()
  await readHeading(page, "3212 Pump Housing")
  await expect(
    page.getByRole("link", { name: "Descargar original.step", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  return page
}

test("reference changes stay in the draft, survive membership updates and cancel together", async (t) => {
  const page = await referencePiece(t)
  await expect(page.getByRole("link", { name: /^Descargar / })).toHaveCount(0)
  await expect(page.getByRole("group", { name: /^Fichero / })).toHaveCount(2)
  await expect(
    page.getByRole("button", { name: "Añadir Escaneo", exact: true }),
  ).toBeEnabled()
  let selectedPath = null
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: selectedPath } }),
  )
  await page
    .getByRole("button", { name: "Cambiar original.step", exact: true })
    .click()
  await expect(
    page.getByRole("textbox", { name: "Nombre de original.step" }),
  ).toBeVisible()
  selectedPath = "Other/invalid.step"
  await page
    .getByRole("button", { name: "Cambiar original.step", exact: true })
    .click()
  await expect(page.getByRole("alert")).toHaveText(
    "Selecciona un archivo dentro de la carpeta de esta pieza.",
  )
  selectedPath = "3212 Pump Housing/replacement.step"
  await page
    .getByRole("button", { name: "Cambiar original.step", exact: true })
    .click()
  await expect(
    page.getByRole("textbox", {
      name: "Nombre de replacement.step",
      exact: true,
    }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Quitar DRW.pdf", exact: true })
    .click()
  await page
    .getByRole("textbox", { name: "Nombre de la pieza" })
    .fill("Draft name")
  await page.getByRole("button", { name: "Desvincular Bolt Eye" }).click()
  await expect(page.getByText("Sin features vinculados.")).toBeVisible()
  await expect(
    page.getByRole("textbox", {
      name: "Nombre de replacement.step",
      exact: true,
    }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(
      () => window.review.requests.filter((r) => r.kind === "part").length,
    ),
    0,
  )
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await readHeading(page, "3212 Pump Housing")
  await expect(
    page.getByRole("link", { name: "Descargar original.step", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Descargar DRW.pdf", exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Editar pieza", exact: true }).click()
  await expect(
    page.getByRole("textbox", { name: "Nombre de original.step" }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Quitar DRW.pdf", exact: true }),
  ).toBeEnabled()
})

test("reference save failure keeps the draft and retry saves header and files without refreshing data", async (t) => {
  const page = await referencePiece(t)
  let selectedPath = "3212 Pump Housing/replacement.step"
  await page.route("**/__native-picker", (route) =>
    route.fulfill({ json: { path: selectedPath } }),
  )
  await page
    .getByRole("button", { name: "Cambiar original.step", exact: true })
    .click()
  await expect(
    page.getByRole("textbox", {
      name: "Nombre de replacement.step",
      exact: true,
    }),
  ).toBeVisible()
  selectedPath = "3212 Pump Housing/scan.stl"
  await page
    .getByRole("button", { name: "Añadir Escaneo", exact: true })
    .click()
  await expect(
    page.getByRole("textbox", { name: "Nombre de scan.stl", exact: true }),
  ).toBeVisible()
  await page
    .getByRole("button", { name: "Quitar DRW.pdf", exact: true })
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
    page.getByRole("textbox", {
      name: "Nombre de replacement.step",
      exact: true,
    }),
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
    page.getByRole("button", { name: "Cambiar replacement.step", exact: true }),
  ).toBeDisabled()
  await expect(
    page.getByRole("button", { name: "Cancelar", exact: true }),
  ).toBeDisabled()
  await page.evaluate(() => window.review.releasePartSave())
  await readHeading(page, "3212 Updated piece")
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
  const patch = await page.evaluate(
    () => window.review.requests.filter((r) => r.kind === "part").at(-1).patch,
  )
  assert.equal(patch.name, "Updated piece")
  assert.equal(patch.code, "3212")
  assert.deepEqual(
    patch.files.map(({ kind, path, name, primary }) => ({
      kind,
      path,
      name,
      primary,
    })),
    [
      {
        kind: "part",
        path: "3212 Pump Housing/replacement.step",
        name: "replacement.step",
        primary: true,
      },
      {
        kind: "scan",
        path: "3212 Pump Housing/scan.stl",
        name: "scan.stl",
        primary: true,
      },
    ],
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

/** Reload the catalogue in the same page: same origin, same browser storage. */
async function reload(page, initialPath = "/") {
  await page.goto("http://component.invalid/")
  await page.evaluate((value) => {
    window.catalogInitialPath = value
  }, initialPath)
  await page.addScriptTag({ content: bundle })
  await page.getByRole("heading", { name: "Catálogo", exact: true }).waitFor()
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).waitFor()
}

test("the catalogue switches between list and grid, remembers it and fits a phone", async (t) => {
  const page = await mount(t)
  const views = page.getByRole("group", { name: "Vista" })
  const results = page.locator("[data-view]")
  await expect(views.getByRole("button", { name: "Lista" })).toHaveAttribute(
    "aria-pressed",
    "true",
  )
  await expect(results).toHaveAttribute("data-view", "list")
  await views.getByRole("button", { name: "Cuadrícula" }).click()
  await expect(results).toHaveAttribute("data-view", "grid")
  const piece = page.getByRole("button", { name: "Abrir 3212 Pump Housing" })
  await expect(piece).toBeVisible()
  await expect(piece.locator("..").getByRole("heading")).toHaveText(
    "3212 Pump Housing",
  )
  await expect(
    piece.locator("..").getByText("Pump Housing · Bosch", { exact: true }),
  ).toBeVisible()
  await expect(
    page
      .getByRole("button", { name: "Abrir Bolt Eye" })
      .locator("..")
      .getByRole("heading", { name: "Bolt Eye", exact: true }),
  ).toBeVisible()
  // Each type keeps the grid.
  for (const kind of ["Piezas", "Features", "Todo"]) {
    await page.getByRole("button", { name: kind, exact: true }).click()
    await expect(results).toHaveAttribute("data-view", "grid")
  }
  // Cotas found by the search stay above the grid.
  await page.getByPlaceholder("Buscar piezas, features o cotas…").fill("170")
  const cotas = page.getByRole("region", { name: "Cotas encontradas" })
  await expect(cotas).toBeVisible()
  const cotasBox = await cotas.boundingBox()
  const gridBox = await results.boundingBox()
  assert.ok(cotasBox.y + cotasBox.height <= gridBox.y)
  await page
    .getByRole("button", { name: "Limpiar busqueda", exact: true })
    .click()

  await reload(page)
  await expect(
    page.getByRole("group", { name: "Vista" }).getByRole("button", {
      name: "Cuadrícula",
    }),
  ).toHaveAttribute("aria-pressed", "true")
  await expect(page.locator("[data-view]")).toHaveAttribute("data-view", "grid")

  await page.setViewportSize({ width: 390, height: 900 })
  const first = await page
    .getByRole("button", { name: "Abrir 3212 Pump Housing" })
    .boundingBox()
  const second = await page
    .getByRole("button", { name: "Abrir Bolt Eye" })
    .boundingBox()
  assert.ok(Math.abs(first.x - second.x) < 2, "one column on a phone")
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await views.getByRole("button", { name: "Lista" }).click()
  await expect(page.locator("[data-view]")).toHaveAttribute("data-view", "list")
})

test("without browser storage the catalogue opens as a list and still switches", async (t) => {
  const page = await browser.newPage()
  const errors = []
  page.on("pageerror", (error) => errors.push(error.message))
  page.setDefaultTimeout(5000)
  t.after(() => page.close())
  await page.addInitScript(() => {
    const { getItem, setItem } = Storage.prototype
    Storage.prototype.getItem = function (key) {
      if (key === "inteplast.catalog-view") throw new Error("Storage blocked")
      return getItem.call(this, key)
    }
    Storage.prototype.setItem = function (key, value) {
      if (key === "inteplast.catalog-view") throw new Error("Storage blocked")
      return setItem.call(this, key, value)
    }
  })
  await page.route("**/*", (route) =>
    route.request().url() === "http://component.invalid/"
      ? route.fulfill({
          contentType: "text/html",
          body: '<html><body><div id="root"></div></body></html>',
        })
      : route.abort(),
  )
  await reload(page)
  await expect(page.locator("[data-view]")).toHaveAttribute("data-view", "list")
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Cuadrícula" })
    .click()
  await expect(page.locator("[data-view]")).toHaveAttribute("data-view", "grid")
  assert.deepEqual(errors, [])
})

/** Click a real node of the graph at its drawn position. */
async function clickNode(page, id) {
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-ready", "true")
  await graph.evaluate((element) => element.scrollIntoView({ block: "center" }))
  const point = await graph.evaluate((element, nodeId) => {
    const instance = element.catalogGraph
    const node = instance.graphData().nodes.find((item) => item.id === nodeId)
    const screen = instance.graph2ScreenCoords(node.x, node.y)
    const box = element.getBoundingClientRect()
    return { x: box.left + screen.x, y: box.top + screen.y }
  }, id)
  // force-graph finds the node under the pointer on a later frame: click once it
  // shows the hand cursor, which it sets only over a node.
  await page.mouse.move(point.x, point.y)
  await expect(graph).toHaveCSS("cursor", "pointer")
  await page.mouse.down()
  await page.mouse.up()
}

test("the graph shows the list's results and clicking a real node opens its page", async (t) => {
  const page = await mount(t)
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Grafo" })
    .click()
  const graph = page.getByTestId("catalog-graph")
  // Pieces and features; families and customers are switched off at first.
  await expect(graph).toHaveAttribute("data-nodes", "2")
  await clickNode(page, "part:part-one")
  await readHeading(page, "3212 Pump Housing")
  await page.evaluate(() => window.review.back())
  await expect(graph).toHaveAttribute("data-nodes", "2")
  await clickNode(page, "feature:feature-one")
  await readHeading(page)
})

test("graph switches add families and customers, which filter the catalogue", async (t) => {
  const page = await mount(t)
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Grafo" })
    .click()
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-nodes", "2")
  await page.getByRole("checkbox", { name: "Familias" }).click()
  await expect(graph).toHaveAttribute("data-nodes", "3")
  await page.getByRole("checkbox", { name: "Clientes" }).click()
  await expect(graph).toHaveAttribute("data-nodes", "4")
  await page.getByRole("checkbox", { name: "Clientes" }).click()
  await expect(graph).toHaveAttribute("data-nodes", "3")
  await clickNode(page, "family:family-pump")
  await page.waitForFunction(
    () => window.review.location().search.family === "family-pump",
  )
  await page.waitForFunction(() =>
    window.review.graphRequests.some(
      (params) => params.familyId === "family-pump",
    ),
  )
})

test("the graph background follows the theme and a cut graph says so", async (t) => {
  const page = await mount(t)
  await page.addStyleTag({
    content:
      ":root { --card: rgb(255, 255, 255) } .dark { --card: rgb(17, 17, 17) }",
  })
  await page.evaluate(() => {
    window.review.graphLimit = 1
  })
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Grafo" })
    .click()
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-background", "rgb(255, 255, 255)")
  await page.evaluate(() => document.documentElement.classList.add("dark"))
  await expect(graph).toHaveAttribute("data-background", "rgb(17, 17, 17)")
  await page.evaluate(() => document.documentElement.classList.remove("dark"))
  await expect(graph).toHaveAttribute("data-background", "rgb(255, 255, 255)")
  // Never a part presented as the whole.
  await expect(
    // The total counts the family and the customer of the piece too.
    page.getByText("Mostrando 1 de 4: filtra para ver el resto", {
      exact: true,
    }),
  ).toBeVisible()
  await expect(graph).toHaveAttribute("data-nodes", "1")
})

test("Planos shows every drawing as a grid, with thumbnails, component and revision", async (t) => {
  const page = await mount(t)
  // The base thumbnail is served; any other one fails and shows the drawing icon.
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
    "base64",
  )
  await page.route("**/thumbnails/**", (route) =>
    route.request().url().includes("drawing-base")
      ? route.fulfill({ contentType: "image/png", body: png })
      : route.abort(),
  )
  await page.evaluate(() => {
    const part = window.review.parts[0]
    window.review.drawings = [
      {
        file: { id: "drawing-base", filename: "base.pdf", version: "v1" },
        name: "base.pdf",
        primary: true,
        part,
        component: "BASE",
        revision: "07",
      },
      {
        file: { id: "drawing-tapa", filename: "tapa.pdf", version: "v1" },
        name: "tapa.pdf",
        primary: false,
        part,
        component: null,
        revision: null,
      },
    ]
    window.review.thumbnailBusy = { "drawing-base": 1 }
  })
  await page.getByRole("button", { name: "Planos", exact: true }).click()
  assert.equal(
    await page.evaluate(() => window.review.location().search.kind),
    "drawing",
  )
  // Always a grid: no view switch here.
  await expect(page.getByRole("group", { name: "Vista" })).toHaveCount(0)
  await expect(page.locator("[data-view=drawings]")).toBeVisible()
  const base = page.getByRole("button", { name: "Abrir plano base.pdf · 3212" })
  const tile = base.locator("..")
  await expect(
    tile.getByText("3212 - Pump Housing", { exact: true }),
  ).toBeVisible()
  await expect(tile.getByText("BASE · rev. 07", { exact: true })).toBeVisible()
  // Busy once: a placeholder, then the server's thumbnail.
  await expect(
    tile.getByRole("img", { name: "Primera página de base.pdf" }),
  ).toHaveAttribute("src", /thumbnails\/drawing-base\.png$/, { timeout: 8000 })
  assert.ok(
    (await page.evaluate(() => window.review.thumbnailRequests)).filter(
      (id) => id === "drawing-base",
    ).length >= 2,
  )
  const tapa = page
    .getByRole("button", { name: "Abrir plano tapa.pdf · 3212" })
    .locator("..")
  await expect(tapa.getByText(/rev\./)).toHaveCount(0)
  await expect(tapa.getByLabel("Sin miniatura")).toBeVisible()
  // Piece filters apply to drawings with the same criterion.
  await page.evaluate(() =>
    window.review.navigate({
      to: "/features",
      search: { kind: "drawing", family: "family-pump" },
    }),
  )
  await page.waitForFunction(() =>
    window.review.drawingRequests.some(
      (params) => params.familyId === "family-pump",
    ),
  )
  await base.click()
  await page.waitForFunction(
    () =>
      window.review.location().pathname ===
      "/parts/part-one/fichero/drawing-base",
  )
})

test("a name with HTML is shown as text in the graph and never runs", async (t) => {
  const page = await mount(t)
  const payload = '<img src=x onerror="window.__graphInjected=1">Bolt'
  await page.evaluate((name) => {
    window.review.feature.name = name
    window.review.parts[0].name = name
  }, payload)
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Grafo" })
    .click()
  const graph = page.getByTestId("catalog-graph")
  await expect(graph).toHaveAttribute("data-ready", "true")
  for (const id of ["feature:feature-one", "part:part-one"]) {
    await graph.evaluate((element) =>
      element.scrollIntoView({ block: "center" }),
    )
    const point = await graph.evaluate((element, nodeId) => {
      const instance = element.catalogGraph
      const node = instance.graphData().nodes.find((item) => item.id === nodeId)
      const screen = instance.graph2ScreenCoords(node.x, node.y)
      const box = element.getBoundingClientRect()
      return { x: box.left + screen.x, y: box.top + screen.y }
    }, id)
    await page.mouse.move(point.x, point.y)
    await expect(graph).toHaveCSS("cursor", "pointer")
    // The tooltip carries the name as text: no element was created from it.
    const tooltip = page.locator(".graph-tooltip")
    await expect(tooltip).toContainText("<img src=x")
    assert.equal(await tooltip.locator("img").count(), 0)
  }
  assert.equal(await page.evaluate(() => window.__graphInjected), undefined)
})

test("the graph pages the cotas found beyond the first 40", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    window.review.cotaCount = 81
  })
  await page
    .getByRole("group", { name: "Vista" })
    .getByRole("button", { name: "Grafo" })
    .click()
  await page.getByPlaceholder("Buscar piezas, features o cotas…").fill("N1")
  const cotas = page.getByRole("region", { name: "Cotas encontradas" })
  await expect(cotas.getByRole("link")).toHaveCount(40)
  await cotas
    .getByRole("button", { name: "Mostrar más cotas (40 de 81)" })
    .click()
  await expect(cotas.getByRole("link")).toHaveCount(80)
  await cotas
    .getByRole("button", { name: "Mostrar más cotas (80 de 81)" })
    .click()
  await expect(cotas.getByRole("link")).toHaveCount(81)
  await expect(cotas.getByRole("button", { name: /Mostrar más/ })).toHaveCount(
    0,
  )
})

for (const view of ["Lista", "Cuadrícula"])
  test(`${view} still pages pieces when there are no cotas`, async (t) => {
    const page = await mount(t)
    await page.evaluate(() => {
      for (let index = 0; index < 45; index++)
        window.review.parts.push({
          id: `extra-${index}`,
          code: String(5000 + index),
          name: `Extra ${index}`,
          characteristic_count: 0,
        })
      window.review.navigate({ to: "/features", search: { kind: "part" } })
    })
    await page
      .getByRole("group", { name: "Vista" })
      .getByRole("button", { name: view })
      .click()
    const results = page.locator("[data-view]")
    const cards = results.getByRole("button", { name: /^Abrir / })
    await expect(cards).toHaveCount(40)
    await expect(
      page.getByRole("region", { name: "Cotas encontradas" }),
    ).toHaveCount(0)
    await page.getByRole("button", { name: "Mostrar más", exact: true }).click()
    await expect(cards).toHaveCount(46)
    await expect(
      page.getByRole("button", { name: "Mostrar más", exact: true }),
    ).toHaveCount(0)
  })
