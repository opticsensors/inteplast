const assert = require("node:assert/strict")
const path = require("node:path")
const { before, after, test } = require("node:test")
const esbuild = require("esbuild")
const { chromium } = require("playwright")
let browser, bundle

before(async () => {
  const result = await esbuild.build({
    entryPoints: [path.join(__dirname, "fixtures/web-preview.jsx")],
    bundle: true,
    write: false,
    format: "iife",
    platform: "browser",
    jsx: "automatic",
    tsconfig: path.resolve(__dirname, "../../tsconfig.json"),
    define: { "process.env.NODE_ENV": '"development"' },
    plugins: [
      {
        name: "preview-fixtures",
        setup(build) {
          build.onResolve({ filter: /^@\/client$/ }, () => ({
            path: path.join(__dirname, "fixtures/preview-api.js"),
          }))
          build.onResolve({ filter: /^\.\/ModelViewer$/ }, () => ({
            path: "model",
            namespace: "fixture",
          }))
          build.onLoad({ filter: /.*/, namespace: "fixture" }, () => ({
            contents:
              "export default function ModelViewer({previewUrl}) {return <div data-model-url={previewUrl}>Ready model</div>}",
            loader: "jsx",
            resolveDir: __dirname,
          }))
        },
      },
    ],
  })
  bundle = result.outputFiles[0].text
  browser = await chromium.launch({ headless: true })
})
after(async () => {
  await browser?.close()
})
async function mount(t) {
  const page = await browser.newPage()
  t.after(() => page.close())
  const errors = []
  page.on("pageerror", (error) => errors.push(error.message))
  await page.route("**/*", (route) =>
    route.fulfill({ contentType: "text/html", body: '<div id="root"></div>' }),
  )
  await page.goto("http://preview.invalid")
  await page.addScriptTag({ content: bundle })
  t.after(() => assert.deepEqual(errors, []))
  return page
}
test("large STL/STEP load their prepared GLB and polling stops after unmount", async (t) => {
  const page = await mount(t)
  await page.getByText("Preparando la vista 3D…", { exact: true }).waitFor()
  await page
    .locator('[data-model-url="/small.glb"]')
    .waitFor({ timeout: 10000 })
  assert.equal(
    await page.evaluate(
      () => window.preview.action("mold.step", 258699834).action,
    ),
    "view",
  )
  assert.equal(
    await page.evaluate(
      () => window.preview.action("large.iges", 258699834).action,
    ),
    "download",
  )
  assert.equal(
    await page.evaluate(() =>
      window.preview.usesPreview("small.stp", 10000000),
    ),
    false,
  )
  await page.evaluate(() => window.preview.unmount())
  const count = await page.evaluate(() => window.preview.calls.length)
  await page.waitForTimeout(2500)
  assert.equal(await page.evaluate(() => window.preview.calls.length), count)
})
test("failed preview offers an explicit retry without fetching the original", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    window.preview.unmount()
    window.preview.states = [
      { state: "error", message: "No se ha podido preparar la vista" },
    ]
  })
  await page.waitForTimeout(50)
  await page.evaluate(() => window.preview.mount())
  await page.getByRole("button", { name: "Reintentar" }).waitFor()
  await page.evaluate(() => {
    window.preview.states = [{ state: "ready", url: "/retried.glb" }]
  })
  await page.getByRole("button", { name: "Reintentar" }).click()
  await page.locator('[data-model-url="/retried.glb"]').waitFor()
  assert.equal(
    await page.evaluate(() =>
      window.preview.calls.some((call) => call.retry === true),
    ),
    true,
  )
})

test("partial geometry keeps a visible warning alongside the model", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => {
    window.preview.unmount()
    window.preview.states = [
      {
        state: "ready",
        url: "/partial.glb",
        message:
          "Vista parcial: algunas superficies no se han podido representar.",
      },
    ]
  })
  await page.waitForTimeout(50)
  await page.evaluate(() => window.preview.mount())
  await page.locator('[data-model-url="/partial.glb"]').waitFor()
  assert.match(await page.getByRole("status").innerText(), /Vista parcial:/)
})
