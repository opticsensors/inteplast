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
    if (route.request().url().endsWith("/__native-picker"))
      return route.fulfill({
        json: {
          path:
            route.request().postDataJSON().kind === "folder"
              ? "2820 Pump Housing"
              : "drawings/drawing.pdf",
        },
      })
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

async function addPart(page, folder = "2820 Pump Housing") {
  await page.evaluate(async (folder) => {
    if (!window.review.parts.some((part) => part.folder_path === folder))
      window.review.parts.push({
        id: `part-${window.review.parts.length + 1}`,
        code: folder.split(" ")[0],
        name: folder,
        folder_path: folder,
      })
    await window.review.refetchParts()
  }, folder)
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await pickParts(page, [folder])
}

/** Tick pieces in the open «Añadir pieza» menu and add them together. */
async function pickParts(page, names) {
  for (const name of names)
    await page.getByRole("menuitemcheckbox", { name, exact: true }).click()
  await page.getByRole("button", { name: /^Añadir \d+ piezas?$/ }).click()
}

test("new feature shows all sections immediately and opening/cancelling creates nothing", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => window.review.navigate("/new"))
  await expect(
    page.getByRole("button", { name: "Añadir advertencia", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Añadir lección aprendida", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Añadir pieza", exact: true }),
  ).toBeVisible()
  assert.deepEqual(
    await page.evaluate(() => window.review.featureCreateRequests ?? []),
    [],
  )
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.deepEqual(
    await page.evaluate(() => window.review.featureCreateRequests ?? []),
    [],
  )
})

test("new feature accepts notes and existing pieces before the first Save", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => window.review.navigate("/new"))
  await page
    .getByRole("button", { name: "Añadir advertencia", exact: true })
    .click()
  await expect(page.getByPlaceholder("Titulo de la nota")).toHaveValue(
    "Nueva advertencia",
  )
  await expect(page.getByPlaceholder("Nombre del feature")).toHaveValue(
    "Nuevo feature",
  )
  await page.getByPlaceholder("Nombre del feature").fill("Feature with content")
  await page.getByPlaceholder("Titulo de la nota").fill("Watch the thickness")
  await page
    .getByRole("button", { name: "Añadir lección aprendida", exact: true })
    .click()
  await expect(page.getByPlaceholder("Titulo de la nota")).toHaveCount(2)
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await pickParts(page, ["3212 - Pump Housing"])
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const result = await page.evaluate(() => ({
    feature: window.review.feature,
    creates: window.review.featureCreateRequests,
    createdId: window.review.createdFeatureId,
  }))
  assert.equal(result.creates.length, 1)
  assert.equal(result.createdId, result.feature.id)
  assert.equal(result.feature.name, "Feature with content")
  assert.equal(result.feature.notes.length, 2)
  assert.equal(result.feature.notes[0].title, "Watch the thickness")
  assert.equal(result.feature.parts[0].id, "part-one")
})

test("concurrent first additions share one feature and retain header edits during creation", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => window.review.navigate("/new"))
  await page.evaluate(() => {
    window.review.holdFeatureCreate = true
  })
  await page
    .getByRole("button", { name: "Añadir advertencia", exact: true })
    .click()
  await page.waitForFunction(() => Boolean(window.review.releaseFeatureCreate))
  await page
    .getByRole("button", { name: "Añadir lección aprendida", exact: true })
    .click()
  await addPart(page)
  await page
    .getByPlaceholder("Nombre del feature")
    .fill("Written while creating")
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  assert.equal(
    await page.getByRole("heading", { name: "Otra pagina abierta" }).count(),
    0,
  )
  await page.evaluate(() => window.review.releaseFeatureCreate())
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.featureCreateRequests.length),
    1,
  )
  assert.equal(await page.evaluate(() => window.review.feature.notes.length), 2)
  assert.equal(await page.evaluate(() => window.review.feature.parts.length), 1)
  assert.equal(
    await page.evaluate(() => window.review.feature.name),
    "Written while creating",
  )
})

test("failed automatic creation keeps the header and retries without creating stray parts", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => window.review.navigate("/new"))
  await page.getByPlaceholder("Nombre del feature").fill("Retained title")
  await page.evaluate(() => {
    window.review.failFeatureCreate = true
  })
  await addPart(page)
  await page.getByRole("button", { name: "Reintentar", exact: true }).waitFor()
  assert.equal(await page.evaluate(() => window.review.parts.length), 2)
  await expect(page.getByPlaceholder("Nombre del feature")).toHaveValue(
    "Retained title",
  )
  await page.evaluate(() => {
    window.review.failFeatureCreate = false
  })
  await page.getByRole("button", { name: "Reintentar", exact: true }).click()
  await expect(
    page.getByRole("textbox", { name: "Nombre de la pieza", exact: true }),
  ).toHaveValue("2820 Pump Housing")
  assert.equal(await page.evaluate(() => window.review.feature.parts.length), 1)
  await expect(page.getByPlaceholder("Nombre del feature")).toHaveValue(
    "Retained title",
  )
})

test("part menu searches registered pieces and existing folders without blank creation", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.parts.push({ id: "shared-part", code: "3197", name: "Pot" })
    await window.review.refetchParts()
  })
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await page.getByRole("textbox", { name: "Buscar pieza" }).fill("pot")
  await pickParts(page, ["3197 - Pot"])
  await page
    .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
    .last()
    .waitFor()
  await page.waitForFunction(() => window.review.feature.parts.length === 2)
  assert.equal(await page.evaluate(() => window.review.parts.length), 2)
  assert.equal(
    await page.evaluate(() => window.review.feature.assets.length),
    1,
  )
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  assert.equal(
    await page
      .getByRole("menuitemcheckbox", { name: "3197 - Pot", exact: true })
      .count(),
    0,
  )
  await expect(
    page.getByRole("menuitem", { name: "Crear nueva pieza", exact: true }),
  ).toHaveCount(0)
  await page.getByRole("textbox", { name: "Buscar pieza" }).fill("2820")
  await expect(
    page.getByRole("menuitemcheckbox", {
      name: "2820 Pump Housing",
      exact: true,
    }),
  ).toHaveCount(0)
})

test("registered-piece search preserves names without listing the source folders", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.sourceFolders = Array.from(
      { length: 205 },
      (_, index) => `${8000 + index} Housing`,
    )
    window.review.parts.push({
      id: "renamed",
      code: "CUSTOM",
      name: "Custom housing",
      folder_path: "8204 Housing",
    })
    await window.review.refetchParts()
  })
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await page.getByRole("textbox", { name: "Buscar pieza" }).fill("CUSTOM")
  await pickParts(page, ["CUSTOM - Custom housing"])
  await page.waitForFunction(() =>
    window.review.feature.parts.some((part) => part.id === "renamed"),
  )
  assert.equal(await page.evaluate(() => window.review.parts.length), 2)
  assert.deepEqual(
    await page.evaluate(() => window.review.sourceRequests ?? []),
    [],
  )
})

test("registered pieces remain selectable while the original folder is unavailable", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.failSource = true
    window.review.parts.push({
      id: "legacy",
      code: "LEGACY",
      name: "Existing piece",
    })
    await window.review.refetchParts()
  })
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await expect(
    page.getByText("No se ha podido cargar toda la lista de piezas."),
  ).toHaveCount(0)
  await pickParts(page, ["LEGACY - Existing piece"])
  await page.waitForFunction(() =>
    window.review.feature.parts.some((part) => part.id === "legacy"),
  )
  assert.deepEqual(
    await page.evaluate(() => window.review.folderRequests ?? []),
    [],
  )
})

test("removing a part removes its full card but leaves the part reusable", async (t) => {
  const { page } = await mount(t)
  await page.getByRole("button", { name: "Quitar 3212", exact: true }).click()
  await page
    .getByRole("region", { name: "Pieza 3212", exact: true })
    .waitFor({ state: "hidden" })
  assert.equal(
    await page
      .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
      .count(),
    0,
  )
  assert.equal(await page.evaluate(() => window.review.parts.length), 1)
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await pickParts(page, ["3212 - Pump Housing"])
  await page
    .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
    .waitFor()
  assert.equal(await page.getByPlaceholder("Nombre del fichero").count(), 0)
})

test("part cards reorder by keyboard, retain drafts and persist after a refresh", async (t) => {
  const { page } = await mount(t)
  await addPart(page)
  await page
    .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
    .last()
    .fill("Reordered part")
  const handle = page.getByRole("button", { name: "Mover pieza 2820" })
  await handle.focus()
  await page.keyboard.press("Space")
  await page.keyboard.press("ArrowUp")
  await page.keyboard.press("Space")
  await page.waitForFunction(
    () =>
      window.review.feature.part_order?.[0] ===
      window.review.feature.parts[1].id,
  )
  await page.evaluate(() => window.review.refetch())
  assert.equal(
    await page
      .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
      .first()
      .inputValue(),
    "Reordered part",
  )
  assert.equal(
    await page.evaluate(() => window.review.feature.assets[0].name),
    "Original asset",
  )
})

async function openCover(page, mode = "image") {
  await page.getByRole("button", { name: /^(Añadir|Editar) portada$/ }).click()
  await page
    .getByRole("tab", {
      name: mode === "cad" ? "CAD" : "Imagen",
      exact: true,
    })
    .click()
}

test("adding a part creates an open editable block, selects its default name and saves identity edits", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Nombre del feature").fill("Pending header")
  await addPart(page)
  const name = page
    .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
    .last()
  await page.waitForFunction(() => window.review.feature.parts.length === 2)
  assert.equal(await name.inputValue(), "2820 Pump Housing")
  assert.deepEqual(
    await name.evaluate((input) => [
      document.activeElement === input,
      input.selectionStart,
      input.selectionEnd,
    ]),
    [true, 0, "2820 Pump Housing".length],
  )
  const toggle = page.getByRole("button", { name: /2820 Pump Housing/ })
  assert.equal(await toggle.getAttribute("aria-expanded"), "true")
  assert.equal(await page.getByRole("dialog").count(), 0)
  assert.equal(await page.getByRole("listbox").count(), 0)
  await name.fill("Carcasa nueva")
  const code = page
    .getByRole("textbox", { name: "Codigo de la pieza", exact: true })
    .last()
  await code.fill("1000")
  await page.waitForFunction(() =>
    window.review.feature.parts.some(
      (part) => part.code === "1000" && part.name === "Carcasa nueva",
    ),
  )
  assert.equal(await name.inputValue(), "Carcasa nueva")
  assert.equal(
    await page.getByPlaceholder("Nombre del feature").inputValue(),
    "Pending header",
  )
})

test("adding multiple parts to an empty feature creates distinct codes and no empty-state messages", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.feature.parts = []
    window.review.feature.assets = []
    await window.review.refetch()
  })
  await addPart(page)
  await page.waitForFunction(() => window.review.feature.parts.length === 1)
  await addPart(page, "3051 Pump Housing")
  await page.waitForFunction(() => window.review.feature.parts.length === 2)
  const parts = await page.evaluate(() => window.review.feature.parts)
  assert.notEqual(parts[0].id, parts[1].id)
  assert.notEqual(parts[0].code, parts[1].code)
  assert.equal(
    await page
      .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
      .count(),
    2,
  )
  assert.equal(
    await page
      .getByText(/Todavia no hay (ninguna pieza|ningun fichero)/)
      .count(),
    0,
  )
})

test("adding a folder reuses the registered part when retrying a failed feature link", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.failPartLinks = true
  })
  await addPart(page)
  await page.getByText("Simulated link failure", { exact: true }).waitFor()
  assert.equal(await page.evaluate(() => window.review.parts.length), 2)
  assert.equal(await page.evaluate(() => window.review.feature.parts.length), 1)
  await page.evaluate(() => {
    window.review.failPartLinks = false
  })
  await page.getByRole("button", { name: "Reintentar", exact: true }).click()
  await page.waitForFunction(() => window.review.feature.parts.length === 2)
  assert.equal(await page.evaluate(() => window.review.parts.length), 2)
})

test("part edits survive folding and failed saves, and Save flushes the corrected draft", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    window.review.failParts = true
  })
  const name = page.getByRole("textbox", {
    name: "Nombre de la pieza",
    exact: true,
  })
  await name.fill("Retained part draft")
  await page
    .getByRole("button", { name: /3212.*Pump Housing|^Desplegar pieza$/ })
    .click()
  await page.waitForFunction(() =>
    window.review.requests.some((item) => item.kind === "part"),
  )
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  assert.equal(
    await page.getByRole("heading", { name: "Otra pagina abierta" }).count(),
    0,
  )
  await page
    .getByRole("button", { name: /3212.*Pump Housing|^Desplegar pieza$/ })
    .click()
  await page.getByRole("alert").waitFor()
  assert.equal(await name.inputValue(), "Retained part draft")
  await page.evaluate(() => {
    window.review.failParts = false
  })
  await name.fill("Saved part draft")
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.parts[0].name),
    "Saved part draft",
  )
})

test("existing parts can still be linked without creating another part", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.parts.push({
      id: "existing-part",
      code: "9999",
      name: "Existing part",
    })
    await window.review.refetchParts()
  })
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  await pickParts(page, ["9999 - Existing part"])
  await page.waitForFunction(() => window.review.feature.parts.length === 2)
  assert.equal(await page.evaluate(() => window.review.parts.length), 2)
  assert.equal(
    await page
      .getByRole("textbox", { name: "Nombre de la pieza", exact: true })
      .last()
      .inputValue(),
    "Existing part",
  )
})

test("several pieces are ticked and added together", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    window.review.parts.push(
      { id: "first-extra", code: "7001", name: "First extra" },
      { id: "second-extra", code: "7002", name: "Second extra" },
    )
    await window.review.refetchParts()
  })
  await page.getByRole("button", { name: "Añadir pieza", exact: true }).click()
  const add = page.getByRole("button", { name: /^Añadir \d+ piezas?$/ })
  await expect(add).toBeDisabled()
  // Ticking keeps the menu open; a new search does not forget what was ticked.
  const search = page.getByRole("textbox", { name: "Buscar pieza" })
  await search.fill("7001")
  await page
    .getByRole("menuitemcheckbox", { name: "7001 - First extra", exact: true })
    .click()
  await search.fill("7002")
  await expect(
    page.getByRole("menuitemcheckbox", { name: "7001 - First extra" }),
  ).toHaveCount(0)
  await page
    .getByRole("menuitemcheckbox", { name: "7002 - Second extra", exact: true })
    .click()
  await expect(add).toHaveText("Añadir 2 piezas")
  await add.click()
  await page.waitForFunction(() => window.review.feature.parts.length === 3)
  assert.deepEqual(
    await page.evaluate(() =>
      window.review.feature.parts.map((part) => part.id).slice(1),
    ),
    ["first-extra", "second-extra"],
  )
  await expect(page.getByRole("menu")).toHaveCount(0)
})

async function applyCover(page) {
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Aplicar", exact: true })
    .click()
  await page.getByRole("dialog").waitFor({ state: "hidden" })
}

/** The feature's own cover on its only piece, as the API returns it. */
async function setCover(page, cad = false) {
  await page.evaluate(async (withCad) => {
    const feature = window.review.feature
    const cover = {
      part_id: "part-one",
      image: {
        id: "saved-image",
        filename: "cover.png",
        content_type: "image/png",
        size: 128,
      },
      cover_3d: null,
      auto_image: null,
    }
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
      cover.cover_3d = {
        asset_id: asset.id,
        part_id: asset.part.id,
        file_id: asset.file.id,
        file_version: "v1",
        faces: [{ mesh: 0, face: 1 }],
        camera: { position: [10, -10, 10], target: [0, 0, 0], up: [0, 0, 1] },
      }
    }
    feature.part_covers = [cover]
    await window.review.refetch()
  }, cad)
}

/** What the API keeps as the cover of the feature on its piece `part-one`. */
const partCover = (page) =>
  page.evaluate(
    () =>
      (window.review.feature.part_covers ?? []).find(
        (cover) => cover.part_id === "part-one",
      ) ?? null,
  )

/** Three pieces: an own cover, only the piece's CAD capture, and nothing. */
async function setThreePieces(page) {
  await page.evaluate(async () => {
    const feature = window.review.feature
    const image = (id) => ({
      id,
      filename: `${id}.png`,
      content_type: "image/png",
      size: 128,
    })
    feature.parts = [
      { id: "part-one", code: "3212", name: "Pump Housing" },
      { id: "part-two", code: "3197", name: "Cover" },
      { id: "part-three", code: "2820", name: "Base" },
    ]
    feature.part_order = ["part-one", "part-two", "part-three"]
    feature.part_covers = [
      {
        part_id: "part-one",
        image: image("saved-image"),
        cover_3d: null,
        auto_image: null,
      },
      {
        part_id: "part-two",
        image: null,
        cover_3d: null,
        auto_image: image("uploaded-image"),
      },
      { part_id: "part-three", image: null, cover_3d: null, auto_image: null },
    ]
    await window.review.refetch()
  })
}

const coverSection = (page) => page.locator('section[aria-label^="Captura"]')

test("with several pieces the cover steps through them; with one it shows only the code", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await page.evaluate(() => window.review.navigate("/cover"))
  const section = coverSection(page)
  await expect(section).toContainText("3212")
  await expect(section).toContainText("1 / 3")
  // Keyboard on the focused capture, then the arrow buttons, wrapping around.
  await page.getByRole("button", { name: "Ampliar portada" }).focus()
  await page.keyboard.press("ArrowRight")
  await expect(section).toContainText("3197")
  await expect(section).toContainText("2 / 3")
  await page.getByRole("button", { name: "Pieza siguiente" }).click()
  await expect(section).toContainText("3 / 3")
  // A piece without any capture shows the icon, with nothing to enlarge.
  await expect(
    page.getByRole("button", { name: "Ampliar portada" }),
  ).toHaveCount(0)
  await page.getByRole("button", { name: "Pieza siguiente" }).click()
  await expect(section).toContainText("1 / 3")
  await page.getByRole("button", { name: "Pieza anterior" }).click()
  await expect(section).toContainText("2820")

  // A finger swipe to the left goes to the next piece without opening anything.
  const swipe = (from, to, target = section) =>
    target.evaluate(
      (element, [start, end]) => {
        const touch = (x) =>
          new Touch({ identifier: 1, target: element, clientX: x, clientY: 50 })
        element.dispatchEvent(
          new TouchEvent("touchstart", {
            bubbles: true,
            touches: [touch(start)],
            changedTouches: [touch(start)],
          }),
        )
        element.dispatchEvent(
          new TouchEvent("touchend", {
            bubbles: true,
            touches: [],
            changedTouches: [touch(end)],
          }),
        )
      },
      [from, to],
    )
  await swipe(200, 100)
  await expect(section).toContainText("1 / 3")
  // Only a click right after the gesture is swallowed, never a later tap.
  await page.waitForTimeout(450)

  // The viewer has the same pieces and moves the page carousel with it.
  await page.getByRole("button", { name: "Ampliar portada" }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog).toContainText("3212")
  await expect(dialog).toContainText("1 / 3")
  await dialog.getByRole("button", { name: "Pieza siguiente" }).click()
  await expect(dialog).toContainText("2 / 3")
  // Over a still image the finger also changes piece in the viewer.
  await swipe(100, 250, dialog.locator('[data-slot="cover-surface"]'))
  await expect(dialog).toContainText("1 / 3")
  await page.waitForTimeout(450)
  await dialog.getByRole("button", { name: "Pieza siguiente" }).click()
  await expect(dialog).toContainText("2 / 3")
  await page.keyboard.press("Escape")
  await expect(section).toContainText("2 / 3")

  await page.evaluate(async () => {
    const feature = window.review.feature
    feature.parts = feature.parts.slice(0, 1)
    feature.part_order = ["part-one"]
    feature.part_covers = feature.part_covers.slice(0, 1)
    await window.review.navigate("/away")
    await window.review.navigate("/cover")
  })
  await expect(coverSection(page)).toContainText("3212")
  await expect(coverSection(page)).not.toContainText("/")
  await expect(page.getByRole("button", { name: /^Pieza / })).toHaveCount(0)
})

/** In the open cover editor: upload an image and apply it to the visible piece. */
async function uploadAndApply(page) {
  await page
    .getByRole("dialog")
    .locator('input[type="file"]')
    .setInputFiles({
      name: "piece.png",
      mimeType: "image/png",
      buffer: Buffer.from("image"),
    })
  const apply = page
    .getByRole("dialog")
    .getByRole("button", { name: "Aplicar", exact: true })
  await expect(apply).toBeEnabled()
  await apply.click()
  // With several pieces the editor stays open for the next one.
  await expect(apply).toBeDisabled()
}

/** Edit-mode covers of the first `count` pieces with uploaded images, then close. */
async function draftCovers(page, count) {
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  const dialog = page.getByRole("dialog")
  await page.getByRole("tab", { name: "Imagen", exact: true }).click()
  for (let index = 0; index < count; index++) {
    if (index) {
      await dialog.getByRole("button", { name: "Pieza siguiente" }).click()
      await expect(dialog).toContainText(`${index + 1} / 3`)
      await page.getByRole("tab", { name: "Imagen", exact: true }).click()
    }
    await uploadAndApply(page)
  }
  await dialog.getByRole("button", { name: "Close", exact: true }).click()
  await expect(dialog).toHaveCount(0)
}

/** The covers each «Guardar» sent, as [piece, image] per request. */
const sentCovers = (page) =>
  page.evaluate(() =>
    window.review.requests
      .filter((item) => item.kind === "feature" && item.patch.part_covers)
      .map((item) =>
        item.patch.part_covers.map((cover) => [cover.part_id, cover.image_id]),
      ),
  )

const save = (page) =>
  page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()

test("series editing keeps one draft per piece, saves them all at once and Cancel drops them", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await page
    .getByRole("button", { name: "Editar portada", exact: true })
    .click()
  const dialog = page.getByRole("dialog")
  await expect(dialog).toContainText("3212")
  await expect(dialog).toContainText("1 / 3")
  await page.getByRole("tab", { name: "Imagen", exact: true }).click()
  await uploadAndApply(page)
  await dialog.getByRole("button", { name: "Pieza siguiente" }).click()
  await expect(dialog).toContainText("2 / 3")
  // No CAD selector: the piece is the one in the carousel.
  await page.getByRole("tab", { name: "CAD", exact: true }).click()
  await expect(dialog.getByRole("combobox")).toHaveCount(0)
  await page.getByRole("tab", { name: "Imagen", exact: true }).click()
  await uploadAndApply(page)
  await dialog.getByRole("button", { name: "Close", exact: true }).click()
  assert.deepEqual(await sentCovers(page), [])
  await save(page)
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  // One request with the header and both covers.
  assert.deepEqual(await sentCovers(page), [
    [
      ["part-one", "uploaded-image"],
      ["part-two", "uploaded-image"],
    ],
  ])

  // Cancelling the page drops every draft.
  await page.evaluate(() => {
    window.review.requests = []
    return window.review.navigate("/")
  })
  await draftCovers(page, 1)
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.deepEqual(await sentCovers(page), [])
})

test("a refused second cover saves nothing: neither the title nor the first cover", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await page.getByPlaceholder("Nombre del feature").fill("New title")
  await draftCovers(page, 2)
  await page.evaluate(() => {
    window.review.failCoverPart = "part-two"
  })
  await save(page)
  await page.getByText("La portada debe ser una imagen.").first().waitFor()
  await page.getByRole("button", { name: "Cancelar", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Original header")
  assert.equal(feature.part_covers[0].image.id, "saved-image")
  assert.equal(feature.part_covers[1].image, null)
})

test("unlinking a piece drops its draft only when the server confirms it", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await draftCovers(page, 2)
  // A failed unlink keeps the piece and its draft.
  await page.evaluate(() => {
    window.review.failUnlink = true
  })
  await page.getByRole("button", { name: "Quitar 3197", exact: true }).click()
  await page.getByText("Simulated unlink failure").first().waitFor()
  await page.evaluate(() => {
    window.review.failUnlink = false
  })
  await page.getByRole("button", { name: "Quitar 3197", exact: true }).click()
  await page.waitForFunction(() =>
    window.review.feature.parts.every((part) => part.id !== "part-two"),
  )
  await expect(
    page.getByRole("button", { name: "Quitar 3197", exact: true }),
  ).toHaveCount(0)
  await save(page)
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  // The other draft is saved; nothing for the removed piece, so no conflict.
  assert.deepEqual(await sentCovers(page), [[["part-one", "uploaded-image"]]])
})

test("a piece removed by someone else is a conflict; the retry keeps the other changes", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await page.getByPlaceholder("Nombre del feature").fill("Title kept for retry")
  await draftCovers(page, 2)
  // Another user unlinks 3197 while this page still shows it.
  await page.evaluate(() => {
    const feature = window.review.feature
    feature.parts = feature.parts.filter((part) => part.id !== "part-two")
    feature.part_covers = feature.part_covers.filter(
      (cover) => cover.part_id !== "part-two",
    )
  })
  await save(page)
  // The warning names the piece; nothing is sent, the page stays.
  await page
    .getByText(/^La pieza 3197 ya no está en este feature/)
    .first()
    .waitFor()
  assert.deepEqual(await sentCovers(page), [])
  let feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Original header")
  assert.equal(feature.part_covers[0].image.id, "saved-image")
  // The page refreshes without 3197 and keeps the title and the 3212 draft.
  await expect(
    page.getByRole("button", { name: "Quitar 3197", exact: true }),
  ).toHaveCount(0)
  await save(page)
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Title kept for retry")
  assert.deepEqual((await sentCovers(page)).at(-1), [
    ["part-one", "uploaded-image"],
  ])
})

test("a piece unlinked between the last read and the save only needs one retry", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await page.getByPlaceholder("Nombre del feature").fill("Title kept for retry")
  await draftCovers(page, 2)
  await page.evaluate(() => {
    window.review.beforeFeatureUpdate = () => {
      delete window.review.beforeFeatureUpdate
      const feature = window.review.feature
      feature.parts = feature.parts.filter((part) => part.id !== "part-two")
      feature.part_covers = feature.part_covers.filter(
        (cover) => cover.part_id !== "part-two",
      )
    }
  })
  await save(page)
  await page
    .getByText(/^La pieza 3197 ya no está en este feature/)
    .first()
    .waitFor()
  let feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Original header")
  assert.equal(feature.part_covers[0].image.id, "saved-image")
  await save(page)
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Title kept for retry")
  assert.deepEqual(await sentCovers(page), [
    [
      ["part-one", "uploaded-image"],
      ["part-two", "uploaded-image"],
    ],
    [["part-one", "uploaded-image"]],
  ])
})

test("an earlier conflict of another kind never hides a piece removed later", async (t) => {
  const { page } = await mount(t)
  await setThreePieces(page)
  await draftCovers(page, 2)
  // First refusal: the CAD of 3212 changed.
  await page.evaluate(() => {
    window.review.changedCadPart = "part-one"
  })
  await save(page)
  await page
    .getByText("El CAD ha cambiado.", { exact: false })
    .first()
    .waitFor()
  // Another user unlinks 3197 and the open page refreshes before the next save.
  await page.evaluate(() => {
    const feature = window.review.feature
    feature.parts = feature.parts.filter((part) => part.id !== "part-two")
    feature.part_covers = feature.part_covers.filter(
      (cover) => cover.part_id !== "part-two",
    )
    return window.review.refetch()
  })
  await expect(
    page.getByRole("button", { name: "Quitar 3197", exact: true }),
  ).toHaveCount(0)
  await save(page)
  await page
    .getByText(/^La pieza 3197 ya no está en este feature/)
    .first()
    .waitFor()
  // Still editing: nothing saved, the page did not close.
  await expect(page.getByPlaceholder("Nombre del feature")).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.feature.part_covers[0].image.id),
    "saved-image",
  )
  // With the CAD of 3212 back, the retry saves its draft and nothing for 3197.
  await page.evaluate(() => {
    window.review.changedCadPart = null
  })
  await save(page)
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.deepEqual((await sentCovers(page)).at(-1), [
    ["part-one", "uploaded-image"],
  ])
})

test("a piece without capture shows the icon, never the feature's own old image", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(() => {
    const feature = window.review.feature
    feature.image = {
      id: "saved-image",
      filename: "old.png",
      content_type: "image/png",
      size: 128,
    }
    feature.part_covers = [
      { part_id: "part-one", image: null, cover_3d: null, auto_image: null },
    ]
    return window.review.navigate("/cover")
  })
  const section = coverSection(page)
  await expect(section).toContainText("3212")
  await expect(section.locator("img")).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: "Ampliar portada" }),
  ).toHaveCount(0)
})

test("removing an own cover in the editor shows the piece's CAD capture again", async (t) => {
  const { page } = await mount(t)
  await page.evaluate(async () => {
    const image = (id) => ({
      id,
      filename: `${id}.png`,
      content_type: "image/png",
      size: 128,
    })
    window.review.feature.part_covers = [
      {
        part_id: "part-one",
        image: image("saved-image"),
        cover_3d: null,
        auto_image: image("uploaded-image"),
      },
    ]
    await window.review.refetch()
  })
  await openCover(page)
  await page.getByRole("button", { name: "Quitar imagen" }).click()
  await page.getByRole("button", { name: "Quitar portada" }).click()
  await page.getByRole("dialog").waitFor({ state: "hidden" })
  // The pencil still has a capture to show: the CAD one, not the empty state.
  await expect(
    page.getByRole("button", { name: "Editar portada", exact: true }),
  ).toBeVisible()
  await expect(
    page
      .getByRole("button", { name: "Editar portada", exact: true })
      .locator("img"),
  ).toHaveAttribute("src", /uploaded-image/)
})

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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Keep my header")
  const cover = await partCover(page)
  assert.equal(cover.image.id, "saved-image")
  assert.deepEqual(cover.cover_3d.faces, [{ mesh: 0, face: 1 }])
})

test("CAD editing stays in one modal, retains selection across tabs and cancels without applying", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await openCover(page, "cad")
  await page.getByRole("button", { name: "Limpiar selección" }).click()
  await expect(page.getByRole("button", { name: "Aplicar" })).toBeDisabled()
  await page.getByRole("tab", { name: "Imagen", exact: true }).click()
  await page.getByRole("tab", { name: "CAD", exact: true }).click()
  await expect(page.getByRole("button", { name: "Aplicar" })).toBeDisabled()
  assert.equal(await page.getByRole("dialog").count(), 1)
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancelar", exact: true })
    .click()
  await openCover(page, "cad")
  await expect(page.getByRole("button", { name: "Aplicar" })).toBeEnabled()
  assert.deepEqual(await page.evaluate(() => window.review.uploadRequests), [])
})

test("removing a CAD cover is a draft until the feature is saved", async (t) => {
  const { page } = await mount(t)
  await setCover(page, true)
  await openCover(page)
  await page.getByRole("button", { name: "Quitar imagen" }).click()
  await page.getByRole("button", { name: "Quitar portada" }).click()
  await page.getByRole("button", { name: "Añadir portada" }).waitFor()
  assert.equal((await partCover(page)).image.id, "saved-image")
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const cover = await partCover(page)
  assert.equal(cover.image, null)
  assert.equal(cover.cover_3d, null)
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
  assert.equal((await partCover(page)).image.id, "saved-image")
})

test("note refresh preserves dirty header fields", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Nombre del feature").fill("Pending header")
  await page
    .getByRole("button", { name: "Añadir advertencia", exact: true })
    .click()
  await page.waitForFunction(() => window.review.feature.notes.length === 2)
  await page.waitForTimeout(50)
  assert.equal(
    await page.getByPlaceholder("Nombre del feature").inputValue(),
    "Pending header",
  )
})

test("folding notes preserves and saves pending drafts", async (t) => {
  const { page } = await mount(t)
  await page.getByRole("button", { name: /^Desplegar / }).click()
  await page.getByPlaceholder("Titulo de la nota").fill("Folded warning")
  await page.getByRole("button", { name: /^Desplegar / }).click()
  await page.waitForFunction(
    () => window.review.feature.notes[0].title === "Folded warning",
  )
  await page.getByRole("button", { name: /^Desplegar / }).click()
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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].title),
    "Saved before leaving",
  )
})

test("navigation flushes pending notes", async (t) => {
  const { page } = await mount(t)
  await page.getByPlaceholder("Titulo de la nota").fill("Saved on navigation")
  await page.getByRole("link", { name: "Otra pagina", exact: true }).click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].title),
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
  assert.equal(await partCover(page), null)
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal((await partCover(page)).image.id, "uploaded-image")
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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
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
  await page
    .getByRole("button", { name: "Iniciar sesión", exact: true })
    .waitFor()
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
    .getByText("Vincula el CAD desde la ficha de la pieza.")
    .waitFor()
  assert.equal(
    await page.getByRole("button", { name: "Ir a Piezas ejemplo" }).count(),
    0,
  )
  await page.keyboard.press("Escape")
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
  assert.equal(await partCover(page), null)
  await page.evaluate(async () => {
    await window.review.refetch()
  })
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const feature = await page.evaluate(() => window.review.feature)
  assert.equal(feature.name, "Pending CAD header")
  const cover = await partCover(page)
  assert.equal(cover.image.id, "uploaded-image")
  assert.equal(cover.cover_3d.asset_id, "asset-one")
  assert.equal(cover.cover_3d.part_id, "part-one")
  assert.equal(cover.cover_3d.file_id, "part-step")
  assert.deepEqual(cover.cover_3d.faces, [{ mesh: 0, face: 1 }])
})

test("pasting a local image replaces a CAD cover and leaves text fields alone", async (t) => {
  const { page } = await mount(t)
  await setCover(page)
  await page.evaluate(async () => {
    window.review.feature.part_covers[0].cover_3d = { asset_id: "old-asset" }
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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  const cover = await partCover(page)
  assert.equal(cover.cover_3d, null)
  assert.equal(cover.image.id, "uploaded-image")
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
  await page
    .getByRole("button", { name: /^Guardar(?: cambios)?$/, exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal((await partCover(page)).image.id, "uploaded-image")
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

test("note images survive folding during upload and Save waits for their reference", async (t) => {
  const { page } = await mount(t)
  const expand = page.getByRole("button", {
    name: "Desplegar Original warning",
    exact: true,
  })
  await expand.click()
  await page.evaluate(() => {
    window.review.holdUploads = true
  })
  await page.getByLabel("Imagen de la nota", { exact: true }).setInputFiles({
    name: "detail.png",
    mimeType: "image/png",
    buffer: Buffer.from("image"),
  })
  await page.waitForFunction(() => Boolean(window.review.releaseUpload))
  await expand.click()
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click()
  assert.equal(
    await page.getByRole("heading", { name: "Otra pagina abierta" }).count(),
    0,
  )
  await page.evaluate(() => window.review.releaseUpload())
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].body),
    "Original body\n\n![detail.png](file:uploaded-image)",
  )
  await page.evaluate(() => window.review.navigate("/"))
  await expand.click()
  await page
    .getByRole("button", { name: "Quitar imagen detail.png", exact: true })
    .click()
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click()
  await page.getByRole("heading", { name: "Otra pagina abierta" }).waitFor()
  assert.equal(
    await page.evaluate(() => window.review.feature.notes[0].body),
    "Original body",
  )
})
