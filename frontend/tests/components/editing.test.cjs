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

async function openCover(page, mode = "image") {
  await page.getByRole("button", { name: /^(Añadir|Editar) portada$/ }).click()
  await page
    .getByRole("tab", {
      name: mode === "cad" ? "CAD" : "Imagen",
      exact: true,
    })
    .click()
}

async function applyCover(page) {
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Aplicar", exact: true })
    .click()
  await page.getByRole("dialog").waitFor({ state: "hidden" })
}

async function setCover(page, cad = false) {
  await page.evaluate(async (withCad) => {
    const feature = window.review.feature
    feature.image = {
      id: "saved-image",
      filename: "cover.png",
      content_type: "image/png",
      size: 128,
    }
    feature.image_id = "saved-image"
    if (withCad) {
      const asset = feature.assets[0]
      asset.kind = "part"
      asset.file = {
        id: "part-step",
        filename: "part.stp",
        content_type: "model/step",
        size: 128,
        version: "v1",
      }
      feature.cover_3d = {
        asset_id: asset.id,
        part_id: asset.part.id,
        file_id: asset.file.id,
        file_version: "v1",
        faces: [{ mesh: 0, face: 1 }],
        camera: { position: [10, -10, 10], target: [0, 0, 0], up: [0, 0, 1] },
      }
    }
    await window.review.refetch()
  }, cad)
}

test("the full image opens one modal, with only the corner close action and keyboard focus restored", async (t) => {
  const { page } = await mount(t)
  await setCover(page)
  await page.evaluate(() => window.review.navigate("/cover"))
  const trigger = page.getByRole("button", {
    name: "Ampliar portada",
    exact: true,
  })
  await trigger.getByRole("img").click()
  const dialog = page.getByRole("dialog")
  await dialog.waitFor()
  assert.equal(
    await dialog.getByRole("img", { name: "Original header" }).count(),
    1,
  )
  assert.equal(await dialog.getByRole("button").count(), 1)
  await page.keyboard.press("Escape")
  await dialog.waitFor({ state: "hidden" })
  assert.equal(
    await trigger.evaluate((element) => document.activeElement === element),
    true,
  )
  await page.keyboard.press("Enter")
  await dialog.getByRole("button", { name: "Close", exact: true }).click()
  await dialog.waitFor({ state: "hidden" })
})

test("CAD starts automatically only in the modal without image toggles", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await page.evaluate(() => window.review.navigate("/cover"))
  assert.equal(
    await page.getByRole("button", { name: "Activar 3D" }).count(),
    0,
  )
  assert.equal(await page.evaluate(() => window.review.canvasMounts ?? 0), 0)
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  const model = page.getByRole("img", { name: "Portada 3D del feature" })
  await model.waitFor()
  assert.equal(
    await page.getByRole("button", { name: /Ver imagen|Activar 3D/ }).count(),
    0,
  )
  assert.equal(await page.evaluate(() => window.review.canvasMounts), 1)
  await page.keyboard.press("Escape")
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await model.waitFor()
  assert.equal(await page.evaluate(() => window.review.canvasMounts), 2)
})

test("an unavailable CAD preserves the saved image in the modal", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await page.evaluate(() => {
    window.review.feature.assets = []
    return window.review.navigate("/cover")
  })
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  await page
    .getByRole("alert")
    .getByText(/El CAD vinculado ha cambiado/)
    .waitFor()
  await page
    .getByRole("dialog")
    .getByRole("img", { name: "Original header" })
    .waitFor()
  await page.keyboard.press("Escape")
  await page.getByRole("dialog").waitFor({ state: "hidden" })
})

test("an empty cover has no enlargement action in consultation", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => window.review.navigate("/cover"))
  assert.equal(await page.getByRole("button").count(), 0)
})

test("closing an image draft leaves the previous cover and unsaved header intact", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await page.getByPlaceholder("Nombre del feature").fill("Keep my header")
  await openCover(page)
  await page
    .getByRole("dialog")
    .locator('input[type="file"]')
    .setInputFiles({
      name: "new.png",
      mimeType: "image/png",
      buffer: Buffer.from("image"),
    })
  await page
    .getByRole("button", { name: "Aplicar" })
    .waitFor({ state: "visible" })
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click()
  await openCover(page)
  assert.equal(
    await page.getByRole("dialog").getByRole("img").getAttribute("alt"),
    "cover.png",
  )
  await page.keyboard.press("Escape")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Keep my header")
  assert.equal(feature.image_id, "saved-image")
  assert.deepEqual(feature.cover_3d.faces, [{ mesh: 0, face: 1 }])
})

test("CAD editing stays in one modal, retains selection across tabs and cancels without applying", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await openCover(page, "cad")
  await page.getByRole("button", { name: "Limpiar selección" }).click()
  assert.equal(
    await page.getByRole("button", { name: "Aplicar" }).isDisabled(),
    true,
  )
  await page.getByRole("tab", { name: "Imagen", exact: true }).click()
  await page.getByRole("tab", { name: "CAD", exact: true }).click()
  assert.equal(
    await page.getByRole("button", { name: "Aplicar" }).isDisabled(),
    true,
  )
  assert.equal(await page.getByRole("dialog").count(), 1)
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancelar", exact: true })
    .click()
  await openCover(page, "cad")
  assert.equal(
    await page.getByRole("button", { name: "Aplicar" }).isEnabled(),
    true,
  )
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
})

test("removing a CAD cover is a draft until the feature is saved", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await openCover(page)
  await page.getByRole("button", { name: "Quitar imagen" }).click()
  await page.getByRole("button", { name: "Quitar portada" }).click()
  await page.getByRole("button", { name: "Añadir portada" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.image_id),
    "saved-image",
  )
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(await page.evaluate(() => window.review.feature.image_id), null)
  assert.equal(await page.evaluate(() => window.review.feature.cover_3d), null)
})

test("a failed upload can be cancelled without blocking the feature or replacing its cover", async (t) => {
  const { page } = await mount(t)
  await setCover(page)
  await openCover(page)
  await page.evaluate(() => {
    window.review.failUploads = true
  })
  await page
    .getByRole("dialog")
    .locator('input[type="file"]')
    .setInputFiles({
      name: "new.png",
      mimeType: "image/png",
      buffer: Buffer.from("image"),
    })
  await page.getByRole("button", { name: "Reintentar" }).waitFor()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancelar", exact: true })
    .click()
  await page.getByRole("link", { name: "Otra pagina", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.image_id),
    "saved-image",
  )
})

test("linking an original preserves the header and uploads no bytes", async (t) => {
  const { page, network } = await mount(t)
  await page.getByPlaceholder("Nombre del feature").fill("Unsaved header")
  await page
    .getByRole("button", { name: "Vincular archivo existente", exact: true })
    .click()
  await page.getByRole("button", { name: "drawings", exact: true }).click()
  await page.getByRole("button", { name: /drawing.pdf/ }).click()
  await page.getByLabel("Revisión del documento (opcional)").fill("07")
  await page.getByRole("button", { name: "Vincular", exact: true }).click()
  await page.waitForFunction(
    () => window.review.feature.assets[0].file?.id === "document-one",
  )
  assert.equal(
    await page.getByPlaceholder("Nombre del feature").inputValue(),
    "Unsaved header",
  )
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
  assert.deepEqual(await page.evaluate(() => window.review.referenceRequests), [
    { path: "drawings/drawing.pdf", revision: "07" },
  ])
  assert.deepEqual(network, [])
})

test("failed source selection can be cancelled without trapping navigation", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.failReferences = true
  })
  await page
    .getByRole("button", { name: "Vincular archivo existente", exact: true })
    .click()
  await page.getByRole("button", { name: "drawings", exact: true }).click()
  await page.getByRole("button", { name: /drawing.pdf/ }).click()
  await page.getByRole("button", { name: "Vincular", exact: true }).click()
  await page.getByRole("alert").getByText("Source unavailable").waitFor()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancelar", exact: true })
    .click()
  await page.getByRole("link", { name: "Otra pagina", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
})

test("missing original can be relinked with its document identity intact", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.fileState = "missing"
    window.review.feature.assets[0].file = {
      id: "existing-document",
      filename: "old.pdf",
      size: 128,
      content_type: "application/pdf",
      source: "local",
      version: "old-version",
      revision: "06",
    }
    await window.review.refetch()
  })
  await page
    .getByText("Archivo no encontrado. Puedes volver a vincularlo.", {
      exact: false,
    })
    .waitFor()
  await page
    .getByRole("button", { name: "Vincular o cambiar archivo", exact: true })
    .click()
  await page.getByLabel("Acción sobre el vínculo").selectOption("relink")
  await page.getByRole("button", { name: "drawings", exact: true }).click()
  await page.getByRole("button", { name: /drawing.pdf/ }).click()
  await page.getByLabel("Revisión del documento (opcional)").fill("07")
  await page
    .getByRole("button", { name: "Actualizar referencia", exact: true })
    .click()
  await page.waitForFunction(
    () => window.review.feature.assets[0].file.version === "version-two",
  )
  assert.equal(
    await page.evaluate(() => window.review.feature.assets[0].file.id),
    "existing-document",
  )
  assert.deepEqual(await page.evaluate(() => window.review.relinkRequests), [
    {
      fileId: "existing-document",
      path: "drawings/drawing.pdf",
      revision: "07",
      expected_version: "old-version",
    },
  ])
})

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

test("cover waits for the upload, applies a draft and saves its reference with the header", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.holdUploads = true
  })
  await openCover(page)
  await page
    .getByRole("dialog")
    .locator('input[type="file"]')
    .first()
    .setInputFiles({
      name: "image.png",
      mimeType: "image/png",
      buffer: Buffer.from("isolated-image-placeholder"),
    })
  await page.waitForFunction(() => Boolean(window.review.releaseUpload))
  assert.equal(
    await page
      .getByRole("button", { name: "Quitar portada", exact: true })
      .isDisabled(),
    true,
  )
  await page.keyboard.press("Escape")
  await page.getByRole("dialog").waitFor()
  await page.evaluate(() => window.review.releaseUpload())
  await page.getByRole("button", { name: "Aplicar", exact: true }).waitFor()
  await applyCover(page)
  assert.equal(
    await page.evaluate(() => window.review.feature.image_id),
    undefined,
  )
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

test("CAD cover explains the missing part STEP without discarding the header", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Nombre del feature").fill("Pending header")
  await openCover(page, "cad")
  await page
    .getByRole("alert")
    .getByText(/Primero sube o vincula un STEP/)
    .waitFor()
  await page.getByRole("button", { name: "Ir a Piezas ejemplo" }).click()
  assert.equal(
    await page.getByPlaceholder("Nombre del feature").inputValue(),
    "Pending header",
  )
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
})

test("CAD cover uploads its image but waits for Save to persist the annotation and header", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    const asset = window.review.feature.assets[0]
    asset.kind = "part"
    asset.file = {
      id: "part-step",
      version: "step-version",
      filename: "part.stp",
      content_type: "model/step",
      size: 100,
    }
    await window.review.refetch()
  })
  await page.getByPlaceholder("Nombre del feature").fill("Pending CAD header")
  await openCover(page, "cad")
  await page.getByRole("button", { name: "Marcar superficie" }).click()
  await page.getByRole("button", { name: "Aplicar" }).click()
  await page.waitForFunction(() => !document.querySelector('[role="dialog"]'))
  assert.equal(
    await page.evaluate(() => window.review.feature.cover_3d),
    undefined,
  )
  await page.evaluate(async () => {
    await window.review.refetch()
  })
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Pending CAD header")
  assert.equal(feature.image_id, "uploaded-image")
  assert.equal(feature.cover_3d.asset_id, "asset-one")
  assert.equal(feature.cover_3d.file_id, "part-step")
  assert.deepEqual(feature.cover_3d.faces, [{ mesh: 0, face: 1 }])
})

test("pasting a local image replaces a CAD cover and leaves text fields alone", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.feature.cover_3d = { asset_id: "old-asset" }
    await window.review.refetch()
  })
  const paste = async (selector) =>
    page.evaluate((target) => {
      const data = new DataTransfer()
      data.items.add(
        new File(["image"], "clipboard.png", { type: "image/png" }),
      )
      document.querySelector(target).dispatchEvent(
        new ClipboardEvent("paste", {
          clipboardData: data,
          bubbles: true,
          cancelable: true,
        }),
      )
    }, selector)
  await paste('input[placeholder="Nombre del feature"]')
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
  await openCover(page)
  await paste('button[aria-label="Seleccionar imagen"]')
  await page.waitForFunction(() => window.review.uploadRequests.length === 1)
  await applyCover(page)
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(await page.evaluate(() => window.review.feature.cover_3d), null)
  assert.equal(
    await page.evaluate(() => window.review.feature.image_id),
    "uploaded-image",
  )
})

test("dropping an image updates the cover through the same upload flow", async (t) => {
  const { page } = await mount(t)
  await openCover(page)
  await page
    .getByRole("button", { name: "Seleccionar imagen", exact: true })
    .evaluate((element) => {
      const data = new DataTransfer()
      data.items.add(new File(["image"], "dropped.png", { type: "image/png" }))
      element.dispatchEvent(
        new DragEvent("drop", {
          dataTransfer: data,
          bubbles: true,
          cancelable: true,
        }),
      )
    })
  await page.waitForFunction(() => window.review.uploadRequests.length === 1)
  await applyCover(page)
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.image_id),
    "uploaded-image",
  )
})

test("feature image picker rejects SVG before uploading", async (t) => {
  const { page } = await mount(t)
  await openCover(page)
  const input = page.getByRole("dialog").locator('input[type="file"]')
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
  await openCover(page)
  const imageBox = page
    .getByRole("dialog")
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
  await page.getByTitle("Descargar SVG", { exact: true }).waitFor()
  await page.getByTitle("Descargar Unverified PDF", { exact: true }).waitFor()
})
