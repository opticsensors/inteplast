const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { build } = require("esbuild")
const { chromium, expect } = require("@playwright/test")

test("a remote revision regenerates the thumbnail despite unchanged CAD IDs; unavailable CAD hides cached images", async (t) => {
  const frontend = path.resolve(__dirname, "../..")
  const result = await build({
    entryPoints: [path.join(__dirname, "fixtures/part-cover.jsx")],
    bundle: true,
    write: false,
    format: "iife",
    platform: "browser",
    jsx: "automatic",
    tsconfig: path.join(frontend, "tsconfig.json"),
    define: { "process.env.NODE_ENV": '"development"' },
    plugins: [
      {
        name: "test-boundaries",
        setup(builder) {
          builder.onResolve({ filter: /^\.\/capturePartCad$/ }, () => ({
            path: path.join(__dirname, "fixtures/part-capture.js"),
          }))
          builder.onResolve({ filter: /(?:^|\/)StepCoverCanvas$/ }, () => ({
            path: path.join(__dirname, "fixtures/cad-canvas.jsx"),
          }))
          builder.onResolve({ filter: /^@\/client$/ }, () => ({
            path: path.join(__dirname, "fixtures/api.js"),
          }))
        },
      },
    ],
  })
  const browser = await chromium.launch({ headless: true })
  t.after(() => browser.close())
  const page = await browser.newPage()
  const errors = []
  page.on("pageerror", (error) => errors.push(error.message))
  await page.route("**/*", (route) =>
    route.fulfill(
      route.request().url().includes("/image/")
        ? {
            contentType: "image/png",
            body: Buffer.from(
              "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOioAAAAASUVORK5CYII=",
              "base64",
            ),
          }
        : { contentType: "text/html", body: '<div id="root"></div>' },
    ),
  )
  await page.goto("http://component.invalid/")
  await page.addScriptTag({ content: result.outputFiles[0].text })
  const image = page.getByRole("img", { name: "Test piece", exact: true })
  await expect(image).toHaveAttribute("src", /image-1\.png$/)
  await page.getByRole("button", { name: "Cambiar CAD remoto" }).click()
  await expect(image).toHaveAttribute("src", /image-2\.png$/)
  assert.deepEqual(
    await page.evaluate(() =>
      window.review.saved.map((body) => body.cad_cache_key),
    ),
    ["remote-v1", "remote-v2"],
  )
  await page.getByRole("button", { name: "CAD no disponible" }).click()
  await expect(image).toHaveCount(0)
  assert.equal(await page.evaluate(() => window.review.captures), 2)
  assert.deepEqual(errors, [])
})
