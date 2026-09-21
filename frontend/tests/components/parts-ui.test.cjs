const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { before, after, test } = require("node:test")
const { chromium, expect } = require("@playwright/test")

const frontend = path.resolve(__dirname, "../..")
const artifacts = path.join(
  os.homedir(),
  ".codex",
  "scratch",
  "inteplast-part-workflow-ui",
)
let server, browser, origin

before(async () => {
  const [{ createServer }, { default: tailwindcss }] = await Promise.all([
    import("vite"),
    import("@tailwindcss/vite"),
  ])
  server = await createServer({
    configFile: false,
    root: frontend,
    logLevel: "error",
    cacheDir: path.join(artifacts, "vite", String(process.pid)),
    optimizeDeps: { entries: [path.join(__dirname, "fixtures/app.jsx")] },
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
        name: "part-workflow-page",
        configureServer(vite) {
          vite.middlewares.use("/parts-test", async (_req, res, next) => {
            try {
              const html = await vite.transformIndexHtml(
                "/parts-test",
                '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root" style="max-width:960px;margin:24px auto;padding:0 12px"></div><script type="module" src="/tests/components/fixtures/app.jsx"></script></body></html>',
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
  fs.mkdirSync(artifacts, { recursive: true })
})

after(async () => {
  await browser?.close()
  await server?.close()
})

async function mount(t, addParts = true) {
  const page = await browser.newPage({
    viewport: { width: 1100, height: 1000 },
  })
  t.after(() => page.close())
  await page.route("**/*", (route) =>
    route.request().url().startsWith(origin) ? route.continue() : route.abort(),
  )
  await page.goto(`${origin}/parts-test`)
  await expect(page.getByPlaceholder("Nombre del feature")).toHaveValue(
    "Original header",
  )
  for (let index = 0; addParts && index < 2; index++) {
    await page
      .getByRole("button", { name: "Anadir pieza", exact: true })
      .click()
    await page
      .getByRole("menuitem", {
        name: index === 0 ? "2820 Pump Housing" : "3051 Pump Housing",
        exact: true,
      })
      .click()
    await expect(page.locator("[data-part-id]")).toHaveCount(index + 2)
  }
  return page
}

async function cotas(page) {
  await page.evaluate(async () => {
    window.review.characteristics = ["N170", "N117", "N178"].map(
      (code, index) => ({
        id: `cota-${index}`,
        part_id: "part-one",
        code,
        revision: "06",
        title: "",
        role: index === 2 ? "context" : "reference",
      }),
    )
    const feature = window.review.feature
    feature.assets[0].file = {
      id: "mold-file",
      filename: "mold.step",
      size: 24000,
      content_type: "application/step",
      source: "upload",
    }
    feature.assets.push({
      id: "drawing-asset",
      kind: "drawing",
      name: "Plano",
      position: 1,
      part: feature.parts[0],
      file: {
        id: "drawing-file",
        filename: "drawing.pdf",
        size: 10000,
        content_type: "application/pdf",
        source: "upload",
      },
    })
    await window.review.refetch()
    await window.review.refetchEvidence()
  })
  const card = page.getByRole("region", { name: "Cotas", exact: true })
  await expect(
    card.getByRole("link", { name: "N170", exact: true }),
  ).toBeVisible()
  return card
}

test("cotas use the file row style, add inline fields and wrap only when needed", async (t) => {
  const page = await mount(t, false)
  const card = await cotas(page)
  const add = card.getByRole("button", { name: "Añadir cota" })
  for (const text of [
    "Cotas de esta pieza",
    "Ver pieza →",
    "Revisión",
    "Relación",
    "Vincular cota",
  ])
    assert.equal(await card.getByText(text, { exact: true }).count(), 0)
  assert.doesNotMatch(await card.innerText(), /rev\.|referencia|contexto/)
  const fileRow = page
    .getByPlaceholder("Nombre del fichero")
    .first()
    .locator("..")
    .first()
  const height = (await card.boundingBox()).height
  assert.equal(height, (await fileRow.boundingBox()).height)
  const last = await card
    .getByRole("link", { name: "N178", exact: true })
    .boundingBox()
  await add.click()
  const input = card.getByRole("textbox", { name: "Nueva cota" })
  await expect(input).toBeFocused()
  assert.equal((await card.boundingBox()).height, height)
  assert.ok((await input.boundingBox()).x > last.x + last.width)
  await input.fill("N1")
  // A normal typing pause must not create the prefix as a separate characteristic.
  await page.waitForTimeout(800)
  assert.deepEqual(
    await page.evaluate(() => window.review.characteristicRequests ?? []),
    [],
  )
  await input.fill("n 113")
  await input.press("Enter")
  await expect(
    card.getByRole("link", { name: "N113", exact: true }),
  ).toBeVisible()
  assert.deepEqual(
    await page.evaluate(() => window.review.characteristicRequests),
    [{ code: "N113", revision: "06", role: "primary" }],
  )
  const drawing = card.getByRole("link", { name: "Buscar N113 en el plano" })
  assert.match(
    await drawing.getAttribute("href"),
    /\/features\/feature-one\/fichero\/drawing-asset\?cota=N113/,
  )
  await add.click()
  await input.fill("N170")
  await input.press("Enter")
  await expect(input).toHaveCount(0)
  assert.equal(
    await card.getByRole("link", { name: "N170", exact: true }).count(),
    1,
  )
  assert.equal(
    await page.evaluate(() => window.review.characteristicRequests.length),
    1,
  )
  assert.equal(
    await page.evaluate(
      () => window.review.characteristics.find((c) => c.code === "N170").role,
    ),
    "reference",
  )
  await card.screenshot({ path: path.join(artifacts, "cotas-edit.png") })
  for (let i = 0; i < 5; i++) await add.click()
  await expect(input).toHaveCount(5)
  assert.ok((await card.boundingBox()).height > height)
  await page.setViewportSize({ width: 390, height: 844 })
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  )
  await card.screenshot({ path: path.join(artifacts, "cotas-wrap-mobile.png") })
})

test("read-only cotas match file height and retain direct drawing and measurement links", async (t) => {
  const page = await mount(t, false)
  await cotas(page)
  await page.evaluate(() => window.review.navigate("/previews"))
  const card = page.getByRole("region", { name: "Cotas", exact: true })
  await expect(card).toBeVisible()
  assert.equal(await card.getByRole("button").count(), 0)
  const fileRow = page
    .getByRole("link", { name: "Descargar mold.step", exact: true })
    .locator("../..")
  assert.equal(
    (await card.boundingBox()).height,
    (await fileRow.boundingBox()).height,
  )
  assert.match(
    await card
      .getByRole("link", { name: "N170", exact: true })
      .getAttribute("href"),
    /\/parts\/part-one\?cota=N170/,
  )
  await page.screenshot({
    path: path.join(artifacts, "cotas-read.png"),
    fullPage: true,
  })
})

test("cota drafts survive failures, can be cancelled and participate in the feature save", async (t) => {
  const page = await mount(t, false)
  const card = await cotas(page)
  const add = card.getByRole("button", { name: "Añadir cota" })
  const input = card.getByRole("textbox", { name: "Nueva cota" })
  await add.click()
  await input.fill("N113")
  await card.getByRole("button", { name: "Quitar nueva cota" }).click()
  await expect(input).toHaveCount(0)
  assert.deepEqual(
    await page.evaluate(() => window.review.characteristicRequests ?? []),
    [],
  )
  await add.click()
  await input.fill("incorrecta")
  await input.press("Enter")
  await expect(card.getByRole("alert")).toBeVisible()
  assert.deepEqual(
    await page.evaluate(() => window.review.characteristicRequests ?? []),
    [],
  )
  await page.evaluate(() => {
    window.review.failCharacteristics = true
  })
  await input.fill("N113")
  await input.press("Enter")
  await expect(input).toBeEnabled()
  await expect(input).toHaveValue("N113")
  await page.evaluate(() => {
    window.review.failCharacteristics = false
  })
  await card.getByRole("button", { name: "Reintentar" }).click()
  await expect(
    card.getByRole("link", { name: "N113", exact: true }),
  ).toBeVisible()
  await page.evaluate(() => {
    window.review.failCharacteristicRemove = true
  })
  await card.getByRole("button", { name: "Quitar N113", exact: true }).click()
  await expect(card.getByRole("alert")).toBeVisible()
  await expect(
    card.getByRole("link", { name: "N113", exact: true }),
  ).toBeVisible()
  await page.evaluate(() => {
    window.review.failCharacteristicRemove = false
  })
  await card.getByRole("button", { name: "Quitar N113", exact: true }).click()
  await expect(
    card.getByRole("link", { name: "N113", exact: true }),
  ).toHaveCount(0)
  await add.click()
  await input.fill("N240")
  await page.evaluate(() => {
    window.review.holdCharacteristics = true
  })
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Otra pagina abierta" }),
  ).toHaveCount(0)
  await page.waitForFunction(() =>
    Boolean(window.review.releaseCharacteristics),
  )
  await page.evaluate(() => window.review.releaseCharacteristics())
  await expect(
    page.getByRole("heading", { name: "Otra pagina abierta" }),
  ).toBeVisible()
  assert.ok(
    await page.evaluate(() =>
      window.review.characteristics.some((c) => c.code === "N240"),
    ),
  )
})

test("adding a cota with no known revision does not fabricate revision 06", async (t) => {
  const page = await mount(t, false)
  await page.evaluate(() => {
    window.review.measurementRevision = null
  })
  const card = page.getByRole("region", { name: "Cotas", exact: true })
  await card.getByRole("button", { name: "Añadir cota" }).click()
  await card.getByRole("textbox", { name: "Nueva cota" }).fill("170.5")
  await card.getByRole("textbox", { name: "Nueva cota" }).press("Enter")
  await expect(
    card.getByRole("link", { name: "N170.5", exact: true }),
  ).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.characteristicRequests[0].revision),
    "sin confirmar",
  )
})

test("folder choices and secondary folder action stay compact on desktop and mobile", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Anadir pieza", exact: true }).click()
  await expect(
    page.getByRole("menuitem", { name: "3197 Pot", exact: true }),
  ).toBeVisible()
  await page.getByRole("menu").screenshot({
    path: path.join(artifacts, "folder-choices.png"),
    animations: "disabled",
  })
  await page.keyboard.press("Escape")
  await page
    .getByRole("button", { name: "Opciones de la pieza", exact: true })
    .last()
    .click()
  await expect(
    page.getByRole("menuitem", {
      name: "Cambiar carpeta de la pieza",
      exact: true,
    }),
  ).toBeVisible()
  await page.getByRole("menu").screenshot({
    path: path.join(artifacts, "folder-secondary-menu.png"),
    animations: "disabled",
  })
  await page.keyboard.press("Escape")
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole("button", { name: "Anadir pieza", exact: true }).click()
  const bounds = await page.getByRole("menu").boundingBox()
  assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= 390)
})

test("new feature exposes every section and the file picker omits redundant metadata", async (t) => {
  const page = await mount(t)
  await page.evaluate(() => window.review.navigate("/new"))
  await expect(page.getByPlaceholder("Nombre del feature")).toHaveValue("")
  for (const label of [
    "Anadir advertencia",
    "Anadir leccion aprendida",
    "Anadir pieza",
  ]) {
    await expect(
      page.getByRole("button", { name: label, exact: true }),
    ).toBeVisible()
  }
  await page.screenshot({
    path: path.join(artifacts, "new-feature.png"),
    fullPage: true,
    animations: "disabled",
  })
  await page.getByRole("button", { name: "Anadir pieza", exact: true }).click()
  await page
    .getByRole("menuitem", { name: "2820 Pump Housing", exact: true })
    .click()
  await page
    .getByRole("button", { name: "Anadir fichero", exact: true })
    .click()
  await page
    .getByRole("button", { name: "Vincular archivo existente", exact: true })
    .click()
  await page.getByRole("button", { name: /drawing.pdf/ }).click()
  const dialog = page.getByRole("dialog")
  await expect(
    dialog.getByRole("button", { name: /drawing.pdf/ }),
  ).toHaveAttribute("aria-pressed", "true")
  await expect(dialog.getByText(/^Seleccionado:/)).toHaveCount(0)
  await expect(dialog.getByRole("textbox")).toHaveCount(0)
  await expect(dialog.getByRole("combobox")).toHaveCount(0)
  await expect(
    dialog.getByText(/Selecciona un archivo de la carpeta compartida/),
  ).toHaveCount(0)
  await dialog.screenshot({
    path: path.join(artifacts, "file-picker.png"),
    animations: "disabled",
  })
  await dialog.getByRole("button", { name: "Vincular", exact: true }).click()
  await expect(page.getByPlaceholder("Nombre del fichero")).toHaveValue(
    "drawing.pdf",
  )
  await expect(page.getByPlaceholder("Nombre del fichero")).toHaveAttribute(
    "readonly",
    "",
  )
  await page.locator("#example-parts-editor").screenshot({
    path: path.join(artifacts, "real-filename-card.png"),
    animations: "disabled",
  })
})

test("pointer sorting visibly moves neighboring cards before dropping and saves the result", async (t) => {
  const page = await mount(t)
  const cards = page.locator(
    "#example-parts-editor [data-part-id]:not([data-dnd-placeholder])",
  )
  const ids = await cards.evaluateAll((items) =>
    items.map((item) => item.dataset.partId),
  )
  const originalFirstY = await cards
    .first()
    .evaluate((element) => element.getBoundingClientRect().top + window.scrollY)
  const handle = page.getByRole("button", {
    name: "Mover pieza 3051",
    exact: true,
  })
  await handle.scrollIntoViewIfNeeded()
  const from = await handle.boundingBox()
  const target = await cards.first().boundingBox()
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2)
  await page.mouse.down()
  await page.mouse.move(from.x + from.width / 2, target.y + 15, { steps: 25 })
  await expect
    .poll(() =>
      cards.evaluateAll((items) => items.map((item) => item.dataset.partId)),
    )
    .toEqual([ids[2], ids[0], ids[1]])
  // Compare document positions: scrolling to the handle must not offset this check.
  await expect
    .poll(() =>
      page
        .locator(`[data-part-id="${ids[0]}"]`)
        .evaluate(
          (element) => element.getBoundingClientRect().top + window.scrollY,
        ),
    )
    .toBeGreaterThan(originalFirstY)
  await page
    .locator("#example-parts-editor")
    .screenshot({ path: path.join(artifacts, "dragging.png") })
  await page.mouse.up()
  await page.waitForFunction(
    (wanted) => window.review.feature.part_order?.join() === wanted.join(),
    [ids[2], ids[0], ids[1]],
  )
  await page.evaluate(() => window.review.refetch())
  await expect(cards.first()).toHaveAttribute("data-part-id", ids[2])
  await expect(page.getByPlaceholder("Nombre del fichero")).toHaveValue(
    "Original asset",
  )
  await page
    .locator("#example-parts-editor")
    .screenshot({ path: path.join(artifacts, "desktop.png") })
})

test("Escape cancels a drag and the piece cards fit a narrow screen", async (t) => {
  const page = await mount(t)
  const cards = page.locator(
    "#example-parts-editor [data-part-id]:not([data-dnd-placeholder])",
  )
  const ids = await cards.evaluateAll((items) =>
    items.map((item) => item.dataset.partId),
  )
  await page
    .getByRole("button", { name: "Mover pieza 3051", exact: true })
    .focus()
  await page.keyboard.press("Space")
  await page.keyboard.press("ArrowUp")
  await page.keyboard.press("Escape")
  await expect(
    page.locator(
      "[data-dnd-dragging], [data-dnd-dropping], [data-dnd-placeholder]",
    ),
  ).toHaveCount(0)
  await expect
    .poll(() =>
      cards.evaluateAll((items) => items.map((item) => item.dataset.partId)),
    )
    .toEqual(ids)
  assert.deepEqual(
    await page.evaluate(() => window.review.feature.part_order),
    ids,
  )
  await page.setViewportSize({ width: 390, height: 1000 })
  const overflow = await page
    .locator("#example-parts-editor")
    .evaluate((element) => element.scrollWidth > element.clientWidth)
  assert.equal(overflow, false)
  await page
    .locator("#example-parts-editor")
    .screenshot({ path: path.join(artifacts, "mobile.png") })
})

for (const section of ["files", "warning", "lesson"]) {
  test(`${section} animate on pointer drag, keep edits and persist independently`, async (t) => {
    const page = await mount(t)
    await page.evaluate(async (section) => {
      const feature = window.review.feature
      if (section === "files") {
        const original = feature.assets[0]
        original.position = 0
        feature.assets.push(
          {
            ...original,
            id: "asset-second",
            name: "Second file",
            kind: "drawing",
            position: 1,
          },
          {
            ...original,
            id: "asset-third",
            name: "Third file",
            kind: "part",
            position: 2,
          },
        )
      } else {
        feature.notes = feature.notes.filter((note) => note.kind !== section)
        for (let position = 0; position < 3; position++) {
          feature.notes.push({
            id: `${section}-${position}`,
            feature_id: feature.id,
            kind: section,
            title: `${section} ${position}`,
            body: "Details retained",
            position,
          })
        }
      }
      await window.review.refetch()
    }, section)
    const ids =
      section === "files"
        ? ["asset-one", "asset-second", "asset-third"]
        : [0, 1, 2].map((index) => `${section}-${index}`)
    const cards = page.locator(
      ids
        .map((id) => `[data-sortable-id="${id}"]:not([data-dnd-placeholder])`)
        .join(","),
    )
    await expect(cards).toHaveCount(3)
    const last = page.locator(`[data-sortable-id="${ids[2]}"]`)
    const input = last.getByRole("textbox").first()
    await input.fill("Edited while sorting")
    await cards.first().scrollIntoViewIfNeeded()
    const originalFirst = await cards.first().boundingBox()
    const handle = last.getByRole("button", { name: /^Mover / })
    const from = await handle.boundingBox()
    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2)
    await page.mouse.down()
    await page.mouse.move(from.x + from.width / 2, originalFirst.y + 10, {
      steps: 25,
    })
    const wanted = [ids[2], ids[0], ids[1]]
    await expect
      .poll(() =>
        cards.evaluateAll((items) =>
          items.map((item) => item.dataset.sortableId),
        ),
      )
      .toEqual(wanted)
    assert.ok(
      (await page.locator(`[data-sortable-id="${ids[0]}"]`).boundingBox()).y >
        originalFirst.y,
    )
    await page.mouse.up()
    await page.waitForFunction(
      ({ section, wanted }) => {
        const rows =
          section === "files"
            ? window.review.feature.assets
            : window.review.feature.notes
        return wanted.every(
          (id, position) =>
            rows.find((row) => row.id === id)?.position === position,
        )
      },
      { section, wanted },
    )
    await page.evaluate(() => window.review.refetch())
    await expect(cards.first().getByRole("textbox").first()).toHaveValue(
      "Edited while sorting",
    )
    await expect
      .poll(() =>
        cards.evaluateAll((items) =>
          items.map((item) => item.dataset.sortableId),
        ),
      )
      .toEqual(wanted)
    assert.deepEqual(
      await page.evaluate(() => window.review.feature.part_order),
      ["part-one", "part-2", "part-3"],
    )
    await expect(page.locator("[data-part-id]")).toHaveCount(3)
    await page.screenshot({
      path: path.join(artifacts, `${section}-sorted.png`),
    })
  })
}

test("file ordering cancels with Escape and a failed save retains the order for retry", async (t) => {
  const page = await mount(t)
  const piece = page.locator('[data-part-id="part-one"]')
  await piece
    .getByRole("button", { name: "Anadir fichero", exact: true })
    .click()
  const cards = piece.locator("[data-sortable-id]:not([data-dnd-placeholder])")
  await expect(cards).toHaveCount(2)
  // Wait for the new row's initial name selection before moving focus to its grip.
  await expect(
    piece.getByPlaceholder("Nombre del fichero").last(),
  ).toBeFocused()
  const handle = piece.getByRole("button", {
    name: "Mover fichero Nuevo fichero",
    exact: true,
  })
  await handle.focus()
  await page.keyboard.press("Space")
  await page.keyboard.press("ArrowUp")
  await page.keyboard.press("Escape")
  await expect(
    page.locator(
      "[data-dnd-dragging], [data-dnd-dropping], [data-dnd-placeholder]",
    ),
  ).toHaveCount(0)
  await expect(cards.first()).toHaveAttribute("data-sortable-id", "asset-one")

  await page.evaluate(() => {
    window.review.failReorder = true
  })
  await handle.focus()
  await page.keyboard.press("Space")
  await page.keyboard.press("ArrowUp")
  await page.keyboard.press("Space")
  await expect(
    piece.getByRole("button", { name: "Reintentar", exact: true }),
  ).toBeVisible()
  await expect(cards.first()).toHaveAttribute("data-sortable-id", "asset-2")
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await expect(page.getByPlaceholder("Nombre del feature")).toBeVisible()
  assert.equal(
    await page.evaluate(() => window.review.feature.assets[0].position),
    0,
  )
  await page.evaluate(() => {
    window.review.failReorder = false
  })
  await piece.getByRole("button", { name: "Reintentar", exact: true }).click()
  await page.waitForFunction(
    () =>
      window.review.feature.assets.find((asset) => asset.id === "asset-2")
        .position === 0,
  )
  await page.getByRole("button", { name: "Guardar", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Otra pagina abierta" }),
  ).toBeVisible()
})

async function addCatalogParts(page, isSuperuser = true) {
  await page.evaluate(async (isSuperuser) => {
    window.review.isSuperuser = isSuperuser
    window.review.parts.push(
      { id: "trial-part", code: "TEST", name: "Pieza de prueba" },
      { id: "used-part", code: "REAL", name: "Pieza compartida" },
    )
    window.review.partUsage = { "used-part": 2 }
    await Promise.all([
      window.review.refetchParts(),
      window.review.refetchUser(),
    ])
  }, isSuperuser)
  await page.getByRole("button", { name: "Anadir pieza", exact: true }).click()
}

test("catalog deletion is direct, keeps the menu open and preserves the current draft", async (t) => {
  const page = await mount(t)
  await page
    .getByPlaceholder("Nombre del feature")
    .fill("Draft kept during deletion")
  await addCatalogParts(page)
  await page.getByRole("textbox", { name: "Buscar pieza" }).fill("TEST")
  await page.evaluate(() => {
    window.review.holdPartDelete = true
  })
  await page
    .getByRole("menuitem", {
      name: "Eliminar TEST - Pieza de prueba",
      exact: true,
    })
    .click()
  await page.waitForFunction(() => Boolean(window.review.releasePartDelete))
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect(page.getByRole("menu")).toBeVisible()
  await expect(
    page.getByRole("menuitem", {
      name: "Eliminar TEST - Pieza de prueba",
      exact: true,
    }),
  ).toHaveAttribute("aria-disabled", "true")
  await page.evaluate(() => window.review.releasePartDelete())
  await expect(
    page.getByRole("menuitem", { name: "TEST - Pieza de prueba", exact: true }),
  ).toHaveCount(0)
  await expect(page.getByRole("menu")).toBeVisible()
  await expect(page.getByRole("textbox", { name: "Buscar pieza" })).toHaveValue(
    "TEST",
  )
  assert.deepEqual(
    await page.evaluate(() => window.review.partDeleteRequests),
    ["trial-part"],
  )
  assert.equal(await page.evaluate(() => window.review.feature.parts.length), 3)
  await expect(page.getByPlaceholder("Nombre del feature")).toHaveValue(
    "Draft kept during deletion",
  )
})

test("catalog shows usage, blocks deletion and still allows reusing shared parts", async (t) => {
  const page = await mount(t)
  await addCatalogParts(page)
  await expect(
    page.getByText("Usada en 2 features", { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("menuitem", { name: "Eliminar REAL - Pieza compartida" }),
  ).toHaveAttribute("aria-disabled", "true")
  await page.getByRole("menu").screenshot({
    path: path.join(artifacts, "catalog-deletion.png"),
    animations: "disabled",
  })
  await page
    .getByRole("menuitem", { name: "REAL - Pieza compartida", exact: true })
    .click()
  await page.waitForFunction(() => window.review.feature.parts.length === 4)
  assert.deepEqual(
    await page.evaluate(() => window.review.partDeleteRequests ?? []),
    [],
  )
  await page.evaluate(async () => {
    window.review.isSuperuser = false
    await window.review.refetchUser()
  })
  await page.getByRole("button", { name: "Anadir pieza", exact: true }).click()
  const restricted = page.getByRole("menuitem", {
    name: "Eliminar TEST - Pieza de prueba",
  })
  await expect(restricted).toHaveAttribute("aria-disabled", "true")
  await expect(restricted.locator("..")).toHaveAttribute(
    "title",
    /Solo un administrador/,
  )
})

test("catalog deletion handles stale usage without a modal and can retry by keyboard", async (t) => {
  const page = await mount(t)
  await addCatalogParts(page)
  await page.evaluate(() => {
    window.review.partUsage["trial-part"] = 1
  })
  await page
    .getByRole("menuitem", {
      name: "Eliminar TEST - Pieza de prueba",
      exact: true,
    })
    .click()
  await expect(
    page.getByText("Pieza usada en otro feature. Desvinculala primero.", {
      exact: true,
    }),
  ).toBeVisible()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect(
    page.getByRole("menuitem", {
      name: "Eliminar TEST - Pieza de prueba",
      exact: true,
    }),
  ).toHaveAttribute("aria-disabled", "true")
  assert.ok(
    await page.evaluate(() =>
      window.review.parts.some((part) => part.id === "trial-part"),
    ),
  )
  await page.evaluate(async () => {
    window.review.partUsage["trial-part"] = 0
    await window.review.refetchParts()
  })
  const trash = page.getByRole("menuitem", {
    name: "Eliminar TEST - Pieza de prueba",
    exact: true,
  })
  await expect(trash).not.toHaveAttribute("aria-disabled", "true")
  await trash.focus()
  await page.keyboard.press("Enter")
  await expect(trash).toHaveCount(0)
  assert.equal(
    await page.evaluate(() =>
      window.review.parts.some((part) => part.id === "trial-part"),
    ),
    false,
  )
})
