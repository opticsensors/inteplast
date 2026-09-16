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
          build.onResolve({ filter: /^\.\/StepCoverCanvas$/ }, () => ({
            path: path.join(__dirname, "fixtures/cad-canvas.jsx"),
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
  await page.getByRole("heading", { name: "Features", exact: true }).waitFor()
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).waitFor()
  return page
}

const readHeading = (page, name = "Bolt Eye") =>
  page.getByRole("heading", { name, exact: true }).waitFor()

test("old home links preserve filters and cards open in read mode", async (t) => {
  const page = await mount(
    t,
    "/?q=3212&category=hole&tag=inyeccion&part=part-one",
  )
  const location = await page.evaluate(() => window.review.location())
  assert.equal(location.pathname, "/features")
  assert.equal(String(location.search.q), "3212")
  assert.equal(location.search.category, "hole")
  assert.equal(location.search.tag, "inyeccion")
  assert.equal(location.search.part, "part-one")
  assert.equal(
    await page.getByRole("link", { name: "Dashboard", exact: true }).count(),
    0,
  )
  await page.getByRole("button", { name: "Abrir Bolt Eye" }).click()
  await readHeading(page)
  assert.equal(await page.getByPlaceholder("Nombre del feature").count(), 0)
  assert.equal(
    await page
      .getByRole("link", { name: "Features", exact: true })
      .getAttribute("data-active"),
    "true",
  )
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Features", exact: true }).waitFor()
  assert.equal(
    await page
      .getByPlaceholder("Feature / pieza / codigo / tag...")
      .inputValue(),
    "3212",
  )
})

test("direct Edit saves into read mode and Back restores the search", async (t) => {
  const page = await mount(t)
  await page.getByPlaceholder("Feature / pieza / codigo / tag...").fill("3212")
  await page.getByRole("button", { name: "Editar", exact: true }).click()
  await page.getByPlaceholder("Nombre del feature").fill("Bolt Eye revisado")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await readHeading(page, "Bolt Eye revisado")
  assert.equal(
    await page.evaluate(() => window.review.location().search.editar),
    undefined,
  )
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Features", exact: true }).waitFor()
  assert.equal(
    await page
      .getByPlaceholder("Feature / pieza / codigo / tag...")
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
  await page.getByRole("heading", { name: "Features", exact: true }).waitFor()
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
  await page.getByRole("heading", { name: "Features", exact: true }).waitFor()
  await page.getByRole("heading", { name: "Todavía no hay features" }).waitFor()
})

test("creating a feature opens its editor and leaves no empty creation page in history", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Nuevo feature", exact: true }).click()
  await page.getByPlaceholder("Nombre del feature").fill("Nuevo nervio")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.waitForFunction(
    () => window.review.location().search.editar === true,
  )
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await readHeading(page, "Nuevo nervio")
  await page.evaluate(() => window.review.back())
  await page.getByRole("heading", { name: "Features", exact: true }).waitFor()
})
