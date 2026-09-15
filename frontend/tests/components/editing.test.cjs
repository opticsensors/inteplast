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
    entryPoints: [path.join(__dirname, "fixtures/app.jsx")],
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
after(async () => {
  await browser?.close()
})

async function mount(t) {
  const page = await browser.newPage()
  page.setDefaultTimeout(5000)
  t.after(() => page.close())
  const network = []
  await page.route("**/*", (route) => {
    if (route.request().url() === "http://component.invalid/") {
      return route.fulfill({
        contentType: "text/html",
        body: '<html><body><div id="root"></div></body></html>',
      })
    }
    network.push(route.request().url())
    return route.abort()
  })
  await page.goto("http://component.invalid/")
  await page.addScriptTag({ content: bundle })
  await page.waitForFunction(
    () =>
      document.querySelector('input[placeholder="Nombre del feature"]')
        ?.value === "Original header",
  )
  return { page, network }
}

test("note refresh preserves dirty header fields", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Nombre del feature").fill("Pending header")
  await page
    .getByRole("button", { name: "Anadir advertencia", exact: true })
    .click()
  await page.waitForFunction(() => window.review.feature.notes.length === 2)
  await page.waitForTimeout(50)
  assert.equal(
    await page.getByPlaceholder("Nombre del feature").inputValue(),
    "Pending header",
  )
})

test("folding notes and files preserves and saves pending drafts", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Titulo de la nota").fill("Folded warning")
  await page.getByRole("button", { name: "Warnings", exact: true }).click()
  await page.getByPlaceholder("Nombre del fichero").fill("Folded asset")
  await page
    .getByRole("button", { name: "Piezas ejemplo", exact: true })
    .click()
  await page.waitForFunction(
    () =>
      window.review.feature.notes[0].title === "Folded warning" &&
      window.review.feature.assets[0].name === "Folded asset",
  )
  await page.getByRole("button", { name: "Warnings", exact: true }).click()
  assert.equal(
    await page.getByPlaceholder("Titulo de la nota").inputValue(),
    "Folded warning",
  )
})

test("server refresh updates untouched editors without writing stale values", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.feature.notes[0].title = "Another editor's warning"
    window.review.feature.assets[0].name = "Another editor's asset"
    await window.review.refetch()
  })
  await page.waitForFunction(
    () =>
      document.querySelector('input[placeholder="Titulo de la nota"]').value ===
      "Another editor's warning",
  )
  await page.waitForTimeout(800)
  assert.deepEqual(await page.evaluate(() => window.review.requests), [])
})

test("Save waits for pending autosave, then leaves", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.delay = 150
  })
  await page.getByPlaceholder("Titulo de la nota").fill("Saved before leaving")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].title),
    "Saved before leaving",
  )
})

test("navigation flushes pending notes and files", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Nombre del fichero").fill("Saved on navigation")
  await page.getByRole("link", { name: "Otra pagina", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.assets[0].name),
    "Saved on navigation",
  )
})

test("Save waits for an image upload and stores its resulting reference", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.delay = 200
  })
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({
      name: "image.png",
      mimeType: "image/png",
      buffer: Buffer.from("isolated-image-placeholder"),
    })
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.image_id),
    "uploaded-image",
  )
})

test("navigation with dirty header offers saving without discarding the draft", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Nombre del feature").fill("Header on navigation")
  await page.getByRole("link", { name: "Otra pagina", exact: true }).click()
  await page.getByRole("dialog").waitFor()
  await page.getByRole("button", { name: "Guardar y salir" }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.name),
    "Header on navigation",
  )
})

test("failed save retains draft and blocks leaving until retry succeeds", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.failNotes = true
  })
  await page.getByPlaceholder("Titulo de la nota").fill("Retain failed draft")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("alert").waitFor()
  assert.equal(
    await page.getByPlaceholder("Titulo de la nota").inputValue(),
    "Retain failed draft",
  )
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].title),
    "Original warning",
  )
  await page.evaluate(() => {
    window.review.failNotes = false
  })
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].title),
    "Retain failed draft",
  )
})

test("edits arriving during a slow save are sent in order", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.delay = 250
  })
  await page.getByPlaceholder("Titulo de la nota").fill("First revision")
  await page.waitForFunction(() =>
    window.review.requests.some((item) => item.kind === "note"),
  )
  await page.getByPlaceholder("Titulo de la nota").fill("Latest revision")
  await page.waitForFunction(
    () => window.review.feature.notes[0].title === "Latest revision",
  )
  assert.deepEqual(
    await page.evaluate(() =>
      window.review.requests
        .filter((item) => item.kind === "note")
        .map((item) => item.patch.title),
    ),
    ["First revision", "Latest revision"],
  )
})

test("download links request authorization metadata without downloading bytes", async (t) => {
  const { page, network } = await mount(t)
  await page.evaluate(() => window.review.navigate("/files"))
  await page.waitForFunction(() =>
    document.querySelector("a")?.href.includes("token=review-only"),
  )
  assert.equal(
    await page
      .getByRole("link", { name: "Descargar prueba" })
      .getAttribute("href"),
    "https://files.invalid/api/v1/files/file-one?token=review-only&download=true",
  )
  assert.deepEqual(await page.evaluate(() => window.review.accessRequests), [
    "file-one",
  ])
  assert.deepEqual(network, [])
})

test("logout flushes pending edits before removing credentials", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Titulo de la nota").fill("Saved before logout")
  await page.getByRole("button", { name: "Cerrar sesion" }).click()
  await page.getByRole("button", { name: "Log In", exact: true }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].title),
    "Saved before logout",
  )
  assert.equal(
    await page.evaluate(() => localStorage.getItem("access_token")),
    null,
  )
})

test("cancelling a blocked logout keeps the session and draft", async (t) => {
  const { page } = await mount(t)
  await page
    .getByPlaceholder("Nombre del feature")
    .fill("Header retained on cancelled logout")
  await page.getByRole("button", { name: "Cerrar sesion" }).click()
  await page.getByRole("button", { name: "Seguir editando" }).click()
  assert.equal(
    await page.getByPlaceholder("Nombre del feature").inputValue(),
    "Header retained on cancelled logout",
  )
  assert.ok(await page.evaluate(() => localStorage.getItem("access_token")))
})

test("feature image picker rejects SVG before uploading", async (t) => {
  const { page } = await mount(t)
  const input = page.locator('input[type="file"]').first()
  assert.equal(
    await input.getAttribute("accept"),
    "image/jpeg,image/png,image/gif,image/webp,image/avif,image/bmp",
  )
  await input.setInputFiles({
    name: "illustration.svg",
    mimeType: "image/svg+xml",
    buffer: Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"/>'),
  })
  await page
    .getByText("Usa una imagen JPEG, PNG, GIF, WebP, AVIF o BMP.", {
      exact: true,
    })
    .waitFor()
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
  assert.equal(await page.evaluate(() => window.review.feature.image), null)
})

test("dropping an unsupported file into the feature image is rejected", async (t) => {
  const { page } = await mount(t)
  const imageBox = page
    .locator('input[type="file"]')
    .first()
    .locator("..")
    .getByRole("button")
    .first()
  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer()
    data.items.add(
      new File(["not a raster image"], "looks-like-an-image.png", {
        type: "application/octet-stream",
      }),
    )
    return data
  })
  await imageBox.dispatchEvent("drop", { dataTransfer: transfer })
  await transfer.dispose()
  await page
    .getByText("Usa una imagen JPEG, PNG, GIF, WebP, AVIF o BMP.", {
      exact: true,
    })
    .waitFor()
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
})

test("file list offers previews only for inline raster and PDF MIME types", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    const files = [
      ["JPEG", "photo.jpg", "image/jpeg"],
      ["PNG", "photo.png", "IMAGE/PNG; charset=binary"],
      ["GIF", "photo.gif", "image/gif"],
      ["WebP", "photo.webp", "image/webp"],
      ["AVIF", "photo.avif", "image/avif"],
      ["BMP", "photo.bmp", "image/bmp"],
      ["SVG", "illustration.svg", "image/svg+xml"],
      ["TIFF", "photo.tiff", "image/tiff"],
      ["PDF", "drawing.bin", "Application/PDF; version=1.7"],
      ["Unverified PDF", "drawing.pdf", "application/octet-stream"],
    ]
    const template = window.review.feature.assets[0]
    window.review.feature.assets = files.map(
      ([name, filename, contentType], index) => ({
        ...template,
        id: `asset-${index}`,
        name,
        file: {
          id: `file-${index}`,
          filename,
          content_type: contentType,
          size: 128,
        },
      }),
    )
    await window.review.navigate("/previews")
  })
  for (const name of ["JPEG", "PNG", "GIF", "WebP", "AVIF", "BMP", "PDF"]) {
    await page.getByTitle(`Ver ${name}`, { exact: true }).waitFor()
  }
  for (const name of ["SVG", "TIFF", "Unverified PDF"]) {
    assert.equal(
      await page.getByTitle(`Ver ${name}`, { exact: true }).count(),
      0,
    )
  }
  await page.getByTitle("Descargar illustration.svg", { exact: true }).waitFor()
  await page.getByTitle("Descargar drawing.pdf", { exact: true }).waitFor()
})
