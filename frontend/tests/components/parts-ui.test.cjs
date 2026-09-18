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

async function mount(t) {
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
  for (let index = 0; index < 2; index++) {
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
  const originalFirst = await cards.first().boundingBox()
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
  const movedFirst = await page
    .locator(`[data-part-id="${ids[0]}"]`)
    .boundingBox()
  assert.ok(
    movedFirst.y > originalFirst.y,
    "The neighboring card must leave a visible insertion space during dragging",
  )
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
