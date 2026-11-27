const assert = require("node:assert/strict")
const crypto = require("node:crypto")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { before, after, test } = require("node:test")
const { chromium, expect } = require("@playwright/test")
const { warmUp } = require("./vite-warm-up.cjs")
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
        "three/examples/jsm/controls/ArcballControls.js",
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
  browser = await chromium.launch({
    headless: true,
    channel: process.env.CAD_BOX_BENCH_CHANNEL,
  })
  await warmUp(browser, `${origin}/cover-test`)
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
      if (url.pathname.endsWith("/preview"))
        return route.fulfill({ status: 409 })
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
      // The feature's own CAD cover on its only piece.
      feature.part_covers = [
        {
          part_id: "part-one",
          image: {
            id: "saved-image",
            filename: "cover.png",
            content_type: "image/png",
            size: 128,
          },
          cover_3d: annotation,
          auto_image: null,
        },
      ]
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

const finishDialogEntrance = (page) =>
  page
    .getByRole("dialog")
    .evaluate((dialog) =>
      Promise.all(
        dialog.getAnimations().map((animation) => animation.finished),
      ),
    )

test("a missing coloured PNG is rendered once for each view and keeps the gray fallback", async (t) => {
  const page = await mount(t)
  await page.evaluate(async () => {
    const state = window.review
    const { FilesService, CatalogService } = await import(
      "/tests/components/fixtures/api.js"
    )
    const feature = state.feature
    const { image, cover_3d: selection } = feature.part_covers[0]
    const cad = feature.assets[0].file
    const partId = selection.part_id
    feature.marked_part_ids = [partId]
    feature.first_marked_part_id = partId
    feature.cover_image = image
    feature.color = "#23844d"
    const layer = {
      feature_id: feature.id,
      name: feature.name,
      color: feature.color,
      selection,
    }
    state.pendingCover = {
      cad,
      image,
      cad_cache_key: "checked",
      face_colors: { key: "layers", layers: [layer], review: {}, images: {} },
    }
    state.coloredPart = {
      id: partId,
      code: "test",
      has_face_marks: true,
      ...state.pendingCover,
    }
    const uploaded = { ...image, id: "uploaded-image" }
    state.renders = []
    FilesService.uploadFile = async ({ formData }) => {
      if (formData.file.type !== "image/png" || formData.file.size < 100)
        throw Error("Expected CAD PNG")
      const bitmap = await createImageBitmap(formData.file)
      const ctx = new OffscreenCanvas(bitmap.width, bitmap.height).getContext(
        "2d",
      )
      ctx.drawImage(bitmap, 0, 0)
      const pixels = ctx.getImageData(0, 0, bitmap.width, bitmap.height).data
      bitmap.close()
      let green = 0,
        red = 0
      for (let i = 0; i < pixels.length; i += 4) {
        const [r, g, b] = pixels.subarray(i, i + 3)
        if (g > r + 25 && g > b + 15) green++
        if (r > g + 25 && r > b + 25) red++
      }
      state.tint = { green, red }
      return uploaded
    }
    CatalogService.saveFaceImage = async ({ requestBody: body }) => {
      if (
        body.geometry_key !== selection.geometry_key ||
        body.source_sha256 !== selection.source_sha256
      )
        throw Error("Incorrect source geometry")
      const key = body.feature_id ?? "part"
      if (body.feature_id)
        await new Promise((resolve) => {
          state.finishCapture = resolve
        })
      state.renders.push(key)
      const colors = state.pendingCover.face_colors
      state.pendingCover = {
        ...state.pendingCover,
        face_colors: {
          ...colors,
          images: { ...colors.images, [key]: uploaded },
        },
      }
      return uploaded
    }
    await state.navigate("/colored-part")
  })
  const png = page.locator('img[src*="uploaded-image"]')
  await expect(png).toBeVisible({ timeout: 30000 })
  await page.evaluate(() => window.review.navigate("/feature-previews"))
  await page.waitForFunction(
    () => typeof window.review.finishCapture === "function",
  )
  const oldRed = page.locator('img[src*="saved-image"]')
  await expect(oldRed).toHaveCount(0)
  await expect(page.getByLabel("Comprobando portada")).toHaveCount(3)
  await expect(
    page.getByRole("button", { name: "Ampliar portada" }),
  ).toBeEnabled()
  await expect(
    page.getByRole("button", { name: "Editar portada" }),
  ).toBeEnabled()
  await page.evaluate(() => window.review.finishCapture())
  await expect(png).toHaveCount(3, { timeout: 30000 })
  await page.evaluate(async () => {
    const { CatalogService } = await import("/tests/components/fixtures/api.js")
    CatalogService.readPartCover = async () => {
      await new Promise((resolve) => {
        window.review.finishCheck = resolve
      })
      return window.review.pendingCover
    }
    void window.review.refetch()
  })
  await page.waitForFunction(
    () => typeof window.review.finishCheck === "function",
  )
  await expect(png).toHaveCount(3)
  await expect(oldRed).toHaveCount(0)
  await page.evaluate(() => window.review.finishCheck())
  const result = await page.evaluate(() => ({
    renders: window.review.renders,
    expected: ["part", window.review.feature.id],
    gray: window.review.pendingCover.image.id,
    original: window.review.feature.part_covers[0].image.id,
    tint: window.review.tint,
  }))
  assert.deepEqual(result.renders, result.expected)
  assert.equal(result.gray, "saved-image")
  assert.equal(result.original, "saved-image")
  assert.ok(result.tint.green > 100, JSON.stringify(result.tint))
  assert.equal(result.tint.red, 0)
})

test("piece legend filters shared CAD faces without rebuilding the viewer", async (t) => {
  const page = await mount(t, { busyWorker: true })
  await page.evaluate(async () => {
    const feature = window.review.feature
    const { image, cover_3d: selection } = feature.part_covers[0]
    const cad = feature.assets[0].file
    const layer = (id, color, faces) => ({
      feature_id: id,
      name: id,
      color,
      selection: { ...selection, faces },
    })
    const layers = [
      layer("Nervios", "#e47c18", selection.faces),
      layer("Planitudes", "#216bc4", [selection.faces[0]]),
    ]
    const metadata = {
      cad,
      image,
      cad_cache_key: "source",
      face_colors: {
        key: "test-colors",
        layers,
        review: {},
        images: { part: image },
      },
    }
    window.review.pendingCover = metadata
    window.review.coloredPart = {
      id: "part-one",
      code: "3205",
      has_face_marks: true,
      ...metadata,
    }
    await window.review.navigate("/colored-part")
  })
  const open = page.getByRole("button", { name: "Ampliar portada" })
  await expect(open.locator("img")).toBeVisible()
  await expect(page.getByText("Nervios", { exact: true })).toHaveCount(0)
  await expect(page.getByText("Planitudes", { exact: true })).toHaveCount(0)
  await open.click()
  const preview = surface(page).locator("img")
  await expect(preview).toBeVisible()
  await expect(preview).toHaveCSS("object-fit", "contain")
  await expect(preview.locator("..")).toHaveCSS(
    "background-color",
    "rgb(244, 245, 247)",
  )
  await screenshot(page, "piece-loading-cad.png")
  await ready(page)
  const dialog = page.getByRole("dialog")
  const shared = dialog.getByText("Varios features", { exact: true })
  const planes = dialog.getByRole("checkbox", { name: "Planitudes" })
  await expect(shared).toBeVisible()
  await screenshot(page, "piece-ready-cad.png")
  const canvas = dialog.locator("canvas")
  await canvas.evaluate((el) => {
    el.dataset.original = "true"
  })
  await planes.uncheck()
  await expect(shared).toHaveCount(0)
  await expect(canvas).toHaveAttribute("data-original", "true")
  await expect(dialog.getByRole("checkbox", { name: "Nervios" })).toBeChecked()
  await planes.check()
  await expect(shared).toBeVisible()
  await planes.uncheck()
  await page.keyboard.press("Escape")
  await open.click()
  await expect(planes).toBeChecked()
})

test("real STEP worker preserves existing cover-v1 surfaces in the wide viewer", async (t) => {
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
  assert.ok(
    box.width > box.height && modal.width > page.viewportSize().width * 0.9,
  )
  assert.ok(
    Math.abs(modal.width - box.width - 34) < 1,
    "only border and 16px padding on each side",
  )
  await screenshot(page, "expanded-cad.png")
  await page.keyboard.press("Escape")
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await ready(page)
  assert.equal(await page.evaluate(() => window.workerStats.started), 1)
  await page.keyboard.press("Escape")
  await page.route("**/files/part-step?*", (route) =>
    route.fulfill({ status: 403 }),
  )
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await expect(page.getByRole("alert")).toContainText("CAD no está disponible")
  await expect(surface(page).locator("canvas")).toHaveCount(0)
  await page.keyboard.press("Escape")
  await page.route("**/files/part-step?*", (route) =>
    route.fulfill({
      contentType: "application/octet-stream",
      body: Buffer.concat([step, Buffer.from("\n")]),
    }),
  )
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await expect(page.getByRole("alert")).toContainText("El CAD ha cambiado")
  await expect(surface(page).locator("canvas")).toHaveCount(0)
})

test("a server GLB restores the saved STEP faces without importing the original", async (t) => {
  const dir = path.join(
    os.homedir(),
    ".codex",
    "scratch",
    "inteplast-cover-tests",
    String(process.pid),
    "glb",
  )
  const glb = require("./prepared-cube.cjs")(dir)
  const page = await mount(t)
  let originals = 0
  await page.route("**/files/part-step?*", (route) => {
    originals++
    return route.abort()
  })
  await page.route("**/cube.glb", (route) =>
    route.fulfill({ path: glb, contentType: "model/gltf-binary" }),
  )
  await page.evaluate(async () => {
    const { FilesService } = await import("/tests/components/fixtures/api.js")
    FilesService.preparePreview = async () => ({
      state: "ready",
      url: "/cube.glb",
    })
    await window.review.navigate("/cover")
  })
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await ready(page)
  assert.equal(await page.evaluate(() => window.workerStats.started), 0)
  assert.equal(originals, 0)
  await page.keyboard.press("Escape")
  await page.route("**/cube.glb", (route) => route.fulfill({ status: 403 }))
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await expect(page.getByRole("alert")).toContainText("CAD no está disponible")
  await expect(surface(page).locator("canvas")).toHaveCount(0)
})

test("a thumbnail and viewer can share STEP preparation and cancel independently", async (t) => {
  const page = await mount(t)
  const result = await page.evaluate(async (data) => {
    const { loadCoverGeometry } = await import(
      "/src/components/Features/coverGeometry.ts"
    )
    const { sha256 } = await import("/src/components/Features/cadCover.ts")
    const bytes = Uint8Array.from(data)
    const hash = await sha256(bytes.buffer)
    const thumbnail = new AbortController()
    const viewer = new AbortController()
    const cancelled = loadCoverGeometry(
      bytes.slice().buffer,
      hash,
      thumbnail.signal,
    ).catch((error) => error.name)
    const kept = loadCoverGeometry(bytes.buffer, hash, viewer.signal)
    thumbnail.abort()
    return [
      await cancelled,
      (await kept).geometryKey,
      window.workerStats.started,
    ]
  }, Array.from(step))
  assert.deepEqual(result, ["AbortError", cover.geometry_key, 1])
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
  test(`editor matches viewer dimensions, with stable tabs and visible actions (${mobile ? "touch" : "desktop"})`, async (t) => {
    const page = await mount(t, { mobile })
    await page.evaluate(() => window.review.navigate("/cover"))
    await page.getByRole("button", { name: "Ampliar portada" }).click()
    await ready(page)
    await finishDialogEntrance(page)
    const viewerBounds = await page.getByRole("dialog").boundingBox(),
      viewerSquare = await surface(page).boundingBox()
    await page.keyboard.press("Escape")
    await page.evaluate(() => window.review.navigate("/"))
    await page
      .getByRole("button", { name: "Editar portada", exact: true })
      .click()
    await ready(page)
    const modal = page.getByRole("dialog")
    await finishDialogEntrance(page)
    const cadBounds = await modal.boundingBox(),
      cadSquare = await surface(page).boundingBox()
    assert.ok(Math.abs(cadBounds.width - viewerBounds.width) < 1)
    assert.ok(Math.abs(cadSquare.width - viewerSquare.width) < 1)
    assert.ok(Math.abs(cadBounds.height - viewerBounds.height) < 1)
    assert.ok(cadSquare.height > page.viewportSize().height / 2)
    const tabs = await modal.getByRole("tablist").boundingBox()
    assert.ok(Math.abs(cadSquare.y - tabs.y - tabs.height - 12) < 1)
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
    }
    assert.ok(Math.abs(cadSquare.x - imageSquare.x) < 1)
    assert.ok(Math.abs(cadSquare.width - imageSquare.width) < 1)
    assert.ok(cadSquare.height > imageSquare.height)
    const cadBottom = cadSquare.y + cadSquare.height
    const imageBottom = imageSquare.y + imageSquare.height
    assert.ok(Math.abs(cadBottom - imageBottom) < 1)
    assert.ok(imageBounds.height >= page.viewportSize().height * 0.89)
    assert.ok(Math.abs(imageBounds.width - imageSquare.width - 34) < 1)
    assert.ok(imageBounds.y >= 0)
    await expect(
      modal.getByRole("button", { name: "Cancelar" }),
    ).toBeInViewport()
    await screenshot(
      page,
      mobile ? "mobile-image-editor.png" : "image-editor.png",
    )
    await page.getByRole("tab", { name: "CAD pieza", exact: true }).click()
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
      1,
      "the viewer and editor reuse the same verified geometry after clearing marks",
    )
  })
}

test("left clicks accumulate CAD faces and a repeated click removes only that face", async (t) => {
  const page = await mount(t)
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  await ready(page)
  await finishDialogEntrance(page)
  await page.getByRole("button", { name: "Limpiar selección" }).click()
  const apply = page.getByRole("button", { name: "Aplicar", exact: true })
  const { x, y, width, height } = await surface(page)
    .locator("canvas")
    .boundingBox()
  const top = () => page.mouse.click(x + width * 0.5, y + height * 0.4)
  const side = () => page.mouse.click(x + width * 0.43, y + height * 0.55)
  await top()
  await expect(apply).toBeEnabled()
  await side()
  await top()
  await expect(apply).toBeEnabled()
  await side()
  await expect(apply).toBeDisabled()
})

test("box selection includes only complete visible cube faces and preserves clicks", async (t) => {
  const page = await mount(t)
  const patches = await page.evaluate(async () => {
    const { overlappingPatches } = await import(
      "/tests/components/fixtures/face-box.js"
    )
    return overlappingPatches()
  })
  assert.deepEqual(patches, ["0:2", "0:4", "0:5"])
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  await ready(page)
  await finishDialogEntrance(page)
  const clear = page.getByRole("button", { name: "Limpiar selección" })
  const count = page.getByLabel("Caras seleccionadas")
  const canvas = surface(page).locator("canvas")
  const b = await canvas.boundingBox()
  async function drag(x1, y1, x2, y2) {
    await page.mouse.move(b.x + b.width * x1, b.y + b.height * y1)
    await page.mouse.down()
    await page.mouse.move(b.x + b.width * x2, b.y + b.height * y2)
    await page.mouse.up()
  }
  await clear.click()
  await drag(0.46, 0.46, 0.54, 0.54)
  await expect(count).toHaveText("0")
  await page.mouse.move(b.x + b.width * 0.05, b.y + b.height * 0.05)
  await page.mouse.down()
  await page.mouse.move(b.x + b.width * 0.95, b.y + b.height * 0.95)
  await page.keyboard.press("Escape")
  await page.mouse.up()
  await expect(page.getByRole("dialog")).toBeVisible()
  await expect(count).toHaveText("0")
  await drag(0.95, 0.95, 0.05, 0.05)
  await expect(count).toHaveText("3")
  await drag(0.05, 0.05, 0.95, 0.95)
  await expect(count).toHaveText("3")
  await canvas.click()
  await expect(count).toHaveText("2")
  await clear.click()
  await page.evaluate(() =>
    window.review.setViewerPreferences({
      cad_controls: "classic",
      cad_projection: "perspective",
    }),
  )
  await page.keyboard.down("Shift")
  await drag(0.05, 0.05, 0.95, 0.95)
  await page.keyboard.up("Shift")
  await expect(count).toHaveText("3")
  await clear.click()
  await drag(0.35, 0.4, 0.6, 0.55)
  await expect(count).toHaveText("0")
  await page.keyboard.down("Shift")
  await drag(0.05, 0.05, 0.95, 0.95)
  await page.keyboard.up("Shift")
  const marked = Number(await count.textContent())
  assert.ok(marked > 0)
  await page.getByRole("button", { name: "Aplicar", exact: true }).click()
  await page
    .getByRole("button", { name: "Guardar", exact: true })
    .click()
  await page.waitForFunction(
    (n) => window.review.feature.part_covers[0].cover_3d.faces.length === n,
    marked,
  )
})

test("changing personal navigation keeps the editor, marks and shared covers intact", async (t) => {
  const page = await mount(t)
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  await ready(page)
  await finishDialogEntrance(page)
  const canvas = surface(page).locator("canvas")
  await canvas.evaluate((el) => {
    el.dataset.original = "yes"
  })
  const fetched = []
  page.on("request", (request) => {
    if (request.url().includes("/files/")) fetched.push(request.url())
  })
  await page.evaluate(async () => {
    const { FilesService } = await import("/tests/components/fixtures/api.js")
    const upload = FilesService.uploadFile
    FilesService.uploadFile = async (args) => {
      const bitmap = await createImageBitmap(args.formData.file)
      window.review.captureSize = [bitmap.width, bitmap.height]
      bitmap.close()
      return upload(args)
    }
    window.review.setViewerPreferences({
      cad_projection: "perspective",
      cad_controls: "classic",
      invert_zoom: true,
    })
    await new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve)),
    )
  })
  await expect(canvas).toHaveAttribute("data-original", "yes")
  await expect(
    page.getByRole("combobox", { name: "Modo de giro" }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: /Elegir el centro de giro/ }),
  ).toHaveCount(0)
  await expect(page.getByRole("radio")).toHaveCount(0)
  assert.equal(await page.evaluate(() => window.workerStats.started), 1)
  assert.equal(await page.evaluate(() => window.review.captureSize), undefined)
  assert.deepEqual(fetched, [])
  const clear = page.getByRole("button", { name: "Limpiar selección" })
  await clear.click()
  const apply = page.getByRole("button", { name: "Aplicar", exact: true })
  await expect(apply).toBeDisabled()
  const { x, y, width, height } = await canvas.boundingBox()
  await page.mouse.click(x + width / 2, y + height / 2)
  await expect(apply).toBeEnabled()
  await apply.click()
  await page.waitForFunction(() => window.review.captureSize)
  const [w, h] = await page.evaluate(() => window.review.captureSize)
  assert.ok(w > 100 && w === h)
})

test("applying a CAD cover in the carousel keeps its live canvas", async (t) => {
  const page = await mount(t)
  await page.evaluate(async () => {
    window.review.holdUploads = true
    window.review.feature.parts.push({ id: "part-two", code: "3205" })
    await window.review.refetch()
  })
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  await ready(page)
  const canvas = surface(page).locator("canvas")
  await canvas.evaluate((el) => {
    el.dataset.original = "yes"
  })
  const apply = page.getByRole("button", { name: "Aplicar", exact: true })
  await apply.click()
  await page.waitForFunction(() => Boolean(window.review.releaseUpload))
  await expect(canvas).toHaveAttribute("data-original", "yes")
  await page.evaluate(() => window.review.releaseUpload())
  await expect(apply).toBeEnabled()
  await expect(canvas).toHaveAttribute("data-original", "yes")
})

test("the same clear control recovers an obsolete saved selection on the current geometry", async (t) => {
  const page = await mount(t)
  await page.evaluate(async () => {
    window.review.feature.part_covers[0].cover_3d.geometry_key =
      "obsolete-geometry"
    await window.review.refetch()
  })
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  await expect(page.getByRole("alert")).toContainText(
    "La geometría ha cambiado",
    { timeout: 20000 },
  )
  await page.getByRole("button", { name: "Limpiar selección" }).click()
  await ready(page)
  await expect(page.getByRole("alert")).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Aplicar" })).toBeDisabled()
  assert.equal(await page.evaluate(() => window.workerStats.started), 1)
})

// Optional local benchmark. Each .glb is a prepared CAD from the project;
// the files stay outside Git and all form/API writes use the test fixture.
const benchDir = process.env.CAD_BOX_BENCH_DIR
const coldBox = process.env.CAD_BOX_BENCH_COLD === "1"
test(
  "CAD box timing on local prepared models",
  { skip: !benchDir },
  async (t) => {
    for (const name of fs
      .readdirSync(benchDir)
      .filter((file) => file.endsWith(".glb"))) {
      const page = await mount(t)
      if (coldBox)
        await page.evaluate(() => {
          window.requestIdleCallback = undefined
        })
      await page.route("https://files.invalid/bench.glb", (route) =>
        route.fulfill({
          path: path.join(benchDir, name),
          contentType: "model/gltf-binary",
        }),
      )
      await page.evaluate(async () => {
        const { FilesService } = await import(
          "/tests/components/fixtures/api.js"
        )
        FilesService.preparePreview = async () => ({
          state: "ready",
          url: "/bench.glb",
        })
        window.review.feature.part_covers = []
        await window.review.refetch()
      })
      await page.getByRole("button", { name: "Cambiar imagen" }).click()
      await page.getByRole("tab", { name: "CAD pieza", exact: true }).click()
      await ready(page)
      await finishDialogEntrance(page)
      const canvas = surface(page).locator("canvas")
      const b = await canvas.boundingBox()
      const gpu = await canvas.evaluate((el) => {
        const gl = el.getContext("webgl2")
        const info = gl.getExtension("WEBGL_debug_renderer_info")
        window.boxSamples = []
        el.addEventListener(
          "pointerup",
          (event) => {
            if (event.button !== 0) return
            const start = performance.now()
            let handler
            window.addEventListener(
              "pointerup",
              () => {
                handler = performance.now() - start
              },
              { once: true },
            )
            requestAnimationFrame(() => {
              const fence = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0)
              gl.flush()
              function poll() {
                if (gl.clientWaitSync(fence, 0, 0) === gl.TIMEOUT_EXPIRED)
                  return setTimeout(poll, 1)
                gl.deleteSync(fence)
                window.boxSamples.push({
                  handler,
                  frame: performance.now() - start,
                })
              }
              poll()
            })
          },
          true,
        )
        return info
          ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL)
          : gl.getParameter(gl.RENDERER)
      })
      const counts = []
      for (let i = 0; i < (coldBox ? 1 : 13); i++) {
        if (i) {
          const clear = page.getByRole("button", { name: "Limpiar selección" })
          if (await clear.isEnabled()) await clear.click()
          if (i % 2 === 0) {
            await page.mouse.move(b.x + b.width * 0.5, b.y + b.height * 0.5)
            await page.mouse.down({ button: "middle" })
            await page.mouse.move(b.x + b.width * 0.53, b.y + b.height * 0.52, {
              steps: 3,
            })
            await page.mouse.up({ button: "middle" })
          }
        }
        const inset = [0.25, 0.35, 0.07, 0.4][i % 4]
        await page.mouse.move(b.x + b.width * inset, b.y + b.height * inset)
        await page.mouse.down()
        await page.mouse.move(
          b.x + b.width * (1 - inset),
          b.y + b.height * (1 - inset),
          { steps: 3 },
        )
        await page.mouse.up()
        await page.waitForFunction((n) => window.boxSamples.length === n, i + 1)
        const count = Number(
          await page.getByLabel("Caras seleccionadas").textContent(),
        )
        if (!count)
          await expect(page.getByText(/El máximo es de 5.000/)).toBeVisible()
        counts.push(count)
      }
      const samples = await page.evaluate(() => window.boxSamples)
      t.diagnostic(
        JSON.stringify({
          name,
          gpu,
          width: b.width,
          height: b.height,
          counts,
          samples,
        }),
      )
      await page.close()
    }
  },
)
