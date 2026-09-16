const assert = require("node:assert/strict")
const crypto = require("node:crypto")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { before, after, test } = require("node:test")
const { chromium, expect } = require("@playwright/test")
const THREE = require("three")

const frontend = path.resolve(__dirname, "../..")
const occtRoot = path.dirname(require.resolve("occt-import-js/package.json"))
const step = fs.readFileSync(
  path.join(occtRoot, "test/testfiles/simple-basic-cube/cube.stp"),
)
let server, browser, origin, cover

before(async () => {
  // The old cover-v1 recipe uses Three's float32 coordinates. Compare a real
  // worker import with this fingerprint so stored face indices remain valid.
  const occt = await require("occt-import-js")()
  const imported = occt.ReadStepFile(new Uint8Array(step), null)
  const meshes = imported.meshes.map((mesh) => {
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(
        Array.from(mesh.attributes.position.array),
        3,
      ),
    )
    geometry.setIndex(Array.from(mesh.index.array))
    return {
      positions: Array.from(geometry.attributes.position.array),
      indices: Array.from(geometry.index.array),
      faces: mesh.brep_faces,
    }
  })
  const digest = (value) =>
    crypto.createHash("sha256").update(value).digest("hex")
  const bounds = new THREE.Box3()
  for (const mesh of meshes) {
    bounds.union(
      new THREE.Box3().setFromBufferAttribute(
        new THREE.Float32BufferAttribute(mesh.positions, 3),
      ),
    )
  }
  const distance = bounds.getSize(new THREE.Vector3()).length() * 0.9
  cover = {
    asset_id: "asset-one",
    part_id: "part-one",
    file_id: "part-step",
    file_version: "v1",
    recipe: "occt-import-js@0.0.23/cover-v1",
    source_sha256: digest(step),
    geometry_key: digest(JSON.stringify(meshes)),
    faces: [
      { mesh: 0, face: 0 },
      { mesh: 0, face: 1 },
    ],
    camera: {
      position: [distance, -distance, distance],
      target: [0, 0, 0],
      up: [0, 0, 1],
    },
  }
  const [{ createServer }, { default: tailwindcss }] = await Promise.all([
    import("vite"),
    import("@tailwindcss/vite"),
  ])
  server = await createServer({
    configFile: false,
    root: frontend,
    cacheDir: path.join(
      os.homedir(),
      ".codex",
      "scratch",
      "inteplast-cover-tests",
      String(process.pid),
    ),
    optimizeDeps: {
      entries: [path.join(__dirname, "fixtures/app.jsx")],
      include: [
        "occt-import-js",
        "three",
        "three/examples/jsm/controls/TrackballControls.js",
      ],
    },
    logLevel: "error",
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
        name: "isolated-cover-page",
        configureServer(vite) {
          vite.middlewares.use("/cover-test", async (_req, res, next) => {
            try {
              const html = await vite.transformIndexHtml(
                "/cover-test",
                '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/tests/components/fixtures/app.jsx"></script></body></html>',
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

async function mount(t, { mobile = false, busyWorker = false } = {}) {
  const context = await browser.newContext({
    viewport: mobile
      ? { width: 390, height: 844 }
      : { width: 1280, height: 860 },
    isMobile: mobile,
    hasTouch: mobile,
  })
  t.after(() => context.close())
  await context.addInitScript(() => {
    window.workerStats = { started: 0, terminated: 0, busy: 0, key: null }
    const OriginalWorker = window.Worker
    window.Worker = class extends OriginalWorker {
      constructor(...args) {
        super(...args)
        window.workerStats.started++
        this.addEventListener("error", (event) => {
          window.workerStats.error = event.message
        })
        this.addEventListener("message", (event) => {
          if (event.data.testBusy) {
            window.workerStats.busy++
            event.stopImmediatePropagation()
          } else if (event.data.geometryKey)
            window.workerStats.key = event.data.geometryKey
        })
      }
      terminate() {
        window.workerStats.terminated++
        super.terminate()
      }
    }
  })
  const unexpected = [],
    errors = []
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url())
    if (url.origin === origin) {
      if (busyWorker && url.pathname.endsWith("/cover.worker.ts")) {
        const response = await route.fetch()
        // Simulate a long synchronous tessellation INSIDE the real worker.
        // A control message is consumed by the test observer before app code.
        return route.fulfill({
          response,
          body: `self.addEventListener('message', () => { self.postMessage({testBusy:true}); const end = performance.now()+5000; while(performance.now()<end) {} }, {once:true});\n${await response.text()}`,
        })
      }
      return route.continue()
    }
    if (url.origin === "https://files.invalid") {
      if (url.pathname.endsWith("/part-step"))
        return route.fulfill({
          contentType: "application/octet-stream",
          body: step,
        })
      if (/\/(saved-image|uploaded-image)$/.test(url.pathname))
        return route.fulfill({
          contentType: "image/svg+xml",
          body: '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400" fill="#f4f5f7"/><path d="M80 140L220 80L320 140L320 270L180 330L80 270Z" fill="#acb3bc"/><ellipse cx="200" cy="145" rx="55" ry="25" fill="#e32636"/></svg>',
        })
    }
    unexpected.push(url.href)
    return route.abort()
  })
  const page = await context.newPage()
  page.setDefaultTimeout(20000)
  page.on("pageerror", (error) => errors.push(error.message))
  await page.goto(`${origin}/cover-test`)
  await page.waitForFunction(
    () =>
      document.querySelector('input[placeholder="Nombre del feature"]')
        ?.value === "Original header",
  )
  await page.waitForLoadState("networkidle")
  await page.evaluate(
    async ({ annotation, size }) => {
      const feature = window.review.feature
      feature.image = {
        id: "saved-image",
        filename: "cover.png",
        content_type: "image/png",
        size: 128,
      }
      feature.cover_3d = annotation
      feature.assets[0].kind = "part"
      feature.assets[0].file = {
        id: "part-step",
        filename: "cube.stp",
        content_type: "model/step",
        size,
        version: "v1",
      }
      await window.review.refetch()
    },
    { annotation: cover, size: step.length },
  )
  t.after(() => {
    assert.deepEqual(unexpected, [])
    assert.deepEqual(errors, [])
  })
  return page
}

const surface = (page) =>
  page.getByRole("dialog").locator('[data-slot="cover-surface"]:visible')
const screenshot = (page, name) =>
  process.env.COVER_REVIEW_DIR
    ? page.screenshot({
        path: path.join(process.env.COVER_REVIEW_DIR, name),
        animations: "disabled",
      })
    : Promise.resolve()
const ready = async (page) => {
  try {
    await expect(
      page.getByRole("button", { name: "Encuadrar", exact: true }),
    ).toBeEnabled({ timeout: 20000 })
  } catch (error) {
    throw new Error(
      `${error.message}\n${await page.locator("body").innerText()}\n${JSON.stringify(await page.evaluate(() => window.workerStats))}`,
    )
  }
}

test("real STEP worker preserves existing cover-v1 surfaces and modal fits its square", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => window.review.navigate("/cover"))
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await ready(page)
  await expect(page.getByRole("status")).toHaveCount(0)
  assert.equal(
    await page.evaluate(() => window.workerStats.key),
    cover.geometry_key,
  )
  assert.equal(
    await page.getByRole("button", { name: /Ver imagen|Activar 3D/ }).count(),
    0,
  )
  const box = await surface(page).boundingBox(),
    modal = await page.getByRole("dialog").boundingBox()
  assert.ok(Math.abs(box.width - box.height) < 1)
  assert.ok(
    Math.abs(modal.width - box.width - 34) < 1,
    "only border and 16px padding on each side",
  )
  await screenshot(page, "expanded-cad.png")
})

for (const method of ["Escape", "Close"]) {
  test(`${method} closes and terminates a busy CAD worker while the saved image stays visible`, async (t) => {
    const page = await mount(t, { busyWorker: true })
    await page.emulateMedia({
      reducedMotion: method === "Escape" ? "reduce" : "no-preference",
    })
    await page.evaluate(() => window.review.navigate("/cover"))
    const trigger = page.getByRole("button", { name: "Ampliar portada" })
    await trigger.click()
    await page.waitForFunction(() => window.workerStats.busy === 1)
    await expect(
      page.getByRole("dialog").getByRole("img", { name: "Original header" }),
    ).toBeVisible()
    await expect(page.getByRole("status")).toHaveText("Cargando modelo CAD…")
    const spinner = page.getByRole("status").locator("svg")
    await expect(spinner).toBeVisible()
    await expect(spinner).toHaveCSS("animation-name", "spin")
    const initialTransform = await spinner.evaluate(
      (element) => getComputedStyle(element).transform,
    )
    await expect
      .poll(() =>
        spinner.evaluate((element) => getComputedStyle(element).transform),
      )
      .not.toBe(initialTransform)
    await screenshot(page, "loading-cad.png")
    const start = Date.now()
    if (method === "Escape") await page.keyboard.press("Escape")
    else
      await page
        .getByRole("dialog")
        .getByRole("button", { name: "Close", exact: true })
        .click()
    await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 1200 })
    assert.ok(Date.now() - start < 1500)
    assert.equal(await page.evaluate(() => window.workerStats.terminated), 1)
    await expect(trigger).toBeFocused()
    await trigger.click()
    await page.waitForFunction(() => window.workerStats.busy === 2)
    await page.keyboard.press("Escape")
    assert.equal(await page.evaluate(() => window.workerStats.terminated), 2)
  })
}

for (const mobile of [false, true]) {
  test(`editor matches viewer width and square, with stable tabs and compact actions (${mobile ? "touch" : "desktop"})`, async (t) => {
    const page = await mount(t, { mobile })
    await page.evaluate(() => window.review.navigate("/cover"))
    await page.getByRole("button", { name: "Ampliar portada" }).click()
    await ready(page)
    const viewerBounds = await page.getByRole("dialog").boundingBox(),
      viewerSquare = await surface(page).boundingBox()
    await page.keyboard.press("Escape")
    await page.evaluate(() => window.review.navigate("/"))
    await page
      .getByRole("button", { name: "Editar portada", exact: true })
      .click()
    await ready(page)
    const modal = page.getByRole("dialog")
    const cadBounds = await modal.boundingBox(),
      cadSquare = await surface(page).boundingBox()
    assert.ok(Math.abs(cadBounds.width - viewerBounds.width) < 1)
    assert.ok(Math.abs(cadSquare.width - viewerSquare.width) < 1)
    assert.ok(Math.abs(cadSquare.height - viewerSquare.height) < 1)
    const cancelBounds = await modal
      .getByRole("button", { name: "Cancelar" })
      .boundingBox()
    assert.ok(
      Math.abs(cancelBounds.y - cadSquare.y - cadSquare.height - 12) < 1,
    )
    await screenshot(page, mobile ? "mobile-cad-editor.png" : "cad-editor.png")
    await page.getByRole("tab", { name: "Imagen", exact: true }).click()
    const imageBounds = await modal.boundingBox(),
      imageSquare = await surface(page).boundingBox()
    for (const field of ["x", "y", "width", "height"]) {
      assert.ok(
        Math.abs(cadBounds[field] - imageBounds[field]) < 1,
        `modal ${field}`,
      )
      assert.ok(
        Math.abs(cadSquare[field] - imageSquare[field]) < 1,
        `square ${field}`,
      )
    }
    assert.ok(Math.abs(imageSquare.width - imageSquare.height) < 1)
    assert.ok(Math.abs(imageBounds.width - imageSquare.width - 34) < 1)
    assert.ok(imageBounds.y >= 0)
    await modal
      .getByRole("button", { name: "Cancelar" })
      .scrollIntoViewIfNeeded()
    await expect(
      modal.getByRole("button", { name: "Cancelar" }),
    ).toBeInViewport()
    await screenshot(
      page,
      mobile ? "mobile-image-editor.png" : "image-editor.png",
    )
    await page.getByRole("tab", { name: "CAD", exact: true }).click()
    await ready(page)
    assert.equal(
      await page
        .getByText(/Se guardará al guardar|Haz clic para marcar/)
        .count(),
      0,
    )
    assert.equal(
      await page.getByRole("button", { name: "Nueva selección" }).count(),
      0,
    )
    const clear = page.getByRole("button", { name: "Limpiar selección" })
    const resetBounds = await page
      .getByRole("button", { name: "Encuadrar" })
      .boundingBox()
    const clearBounds = await clear.boundingBox()
    assert.equal(clearBounds.y, resetBounds.y)
    assert.ok(clearBounds.x < resetBounds.x)
    await clear.click()
    await expect(page.getByRole("button", { name: "Aplicar" })).toBeDisabled()
    assert.equal(
      await page.evaluate(() => window.workerStats.started),
      2,
      "clearing marks does not reimport the CAD",
    )
  })
}

test("the same clear control recovers an obsolete saved selection on the current geometry", async (t) => {
  const page = await mount(t)
  await page.evaluate(async () => {
    window.review.feature.cover_3d.geometry_key = "obsolete-geometry"
    await window.review.refetch()
  })
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  await page
    .getByRole("alert")
    .getByText(/La geometría ha cambiado/)
    .waitFor()
  await page.getByRole("button", { name: "Limpiar selección" }).click()
  await ready(page)
  await expect(page.getByRole("alert")).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Aplicar" })).toBeDisabled()
  assert.equal(await page.evaluate(() => window.workerStats.started), 2)
})
