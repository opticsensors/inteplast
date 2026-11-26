const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const { before, after, test } = require("node:test")
const esbuild = require("esbuild")
const { chromium } = require("playwright")

const frontend = path.resolve(__dirname, "../..")
let browser, bundle, worker
// Two vector sheets with different colors. No customer files or external requests.
function syntheticPdf(rotateSecond = false) {
  const stream = (color) => `${color} rg 80 80 180 180 re f`
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Resources << >> /Contents 4 0 R >>",
    `<< /Length ${stream("1 0 0").length} >>\nstream\n${stream("1 0 0")}\nendstream`,
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Rotate ${rotateSecond ? 90 : 0} /Resources << >> /Contents 6 0 R >>`,
    `<< /Length ${stream("0 0 1").length} >>\nstream\n${stream("0 0 1")}\nendstream`,
  ]
  let pdf = "%PDF-1.7\n"
  const offsets = [0]
  objects.forEach((object, i) => {
    offsets.push(Buffer.byteLength(pdf))
    pdf += `${i + 1} 0 obj\n${object}\nendobj\n`
  })
  const xref = Buffer.byteLength(pdf)
  pdf += `xref\n0 7\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`)
    .join("")}trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`
  return pdf
}

before(async () => {
  const result = await esbuild.build({
    entryPoints: [path.join(__dirname, "fixtures/viewers.jsx")],
    bundle: true,
    write: false,
    format: "esm",
    platform: "browser",
    jsx: "automatic",
    tsconfig: path.join(frontend, "tsconfig.json"),
    define: { "process.env.NODE_ENV": '"development"' },
    plugins: [
      {
        name: "isolated-viewers",
        setup(build) {
          build.onResolve({ filter: /^@\/client$/ }, () => ({
            path: path.join(__dirname, "fixtures/viewer-api.js"),
          }))
          build.onResolve({ filter: /pdf\.worker\.min\.mjs\?url$/ }, () => ({
            path: "worker",
            namespace: "worker-url",
          }))
          build.onLoad({ filter: /.*/, namespace: "worker-url" }, () => ({
            contents: 'export default "/worker.mjs"',
            loader: "js",
          }))
        },
      },
    ],
  })
  bundle = result.outputFiles[0].text
  worker = fs.readFileSync(
    require.resolve("pdfjs-dist/build/pdf.worker.min.mjs"),
  )
  browser = await chromium.launch({ headless: true })
})
after(async () => {
  await browser?.close()
})

async function mount(t, mode = "pdf") {
  const context = await browser.newContext({
    viewport: { width: 1000, height: 800 },
  })
  t.after(() => context.close())
  const page = await context.newPage()
  page.setDefaultTimeout(10000)
  const errors = [],
    unexpected = []
  page.on("pageerror", (error) => errors.push(error.message))
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url())
    if (url.origin !== "http://viewer.invalid") {
      unexpected.push(url.href)
      return route.abort()
    }
    if (url.pathname === "/app.js")
      return route.fulfill({ contentType: "text/javascript", body: bundle })
    if (url.pathname === "/worker.mjs")
      return route.fulfill({ contentType: "text/javascript", body: worker })
    if (url.pathname === "/original.pdf")
      return route.fulfill({
        contentType: "application/pdf",
        body: syntheticPdf(mode === "rotated"),
      })
    if (url.pathname === "/")
      return route.fulfill({
        contentType: "text/html",
        body: `<html><head><style>
      body{margin:0} #root>div{position:relative;width:800px;height:600px;overflow:hidden}
      [role=application]{width:100%;height:100%;overflow:hidden;touch-action:none}
      [role=application] canvas{position:absolute;left:0;top:0;transform-origin:top left;pointer-events:none}
      #root>div>div:last-child:not([role]){position:absolute;right:0;top:0}
      button{padding:6px}
      </style></head><body><div id="root"></div><script type="module" src="/app.js"></script></body></html>`,
      })
    unexpected.push(url.href)
    return route.abort()
  })
  await page.goto(`http://viewer.invalid/#${mode}`)
  await page.waitForFunction(() => Boolean(window.viewer))
  t.after(() => {
    assert.deepEqual(errors, [])
    assert.deepEqual(unexpected, [])
  })
  return page
}

test("PDF wheel holds the point under the cursor and drag follows the pointer", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Encuadrar", exact: true }).waitFor()
  const canvas = page.locator("canvas")
  const before = await canvas.boundingBox()
  const cursor = { x: 530, y: 270 }
  const point = {
    x: (cursor.x - before.x) / before.width,
    y: (cursor.y - before.y) / before.height,
  }
  await page.mouse.move(cursor.x, cursor.y)
  await page.mouse.wheel(0, -180)
  await page.waitForFunction(
    (width) =>
      document.querySelector("canvas").getBoundingClientRect().width > width,
    before.width,
  )
  const zoomed = await canvas.boundingBox()
  assert.ok(Math.abs(zoomed.x + zoomed.width * point.x - cursor.x) < 1)
  assert.ok(Math.abs(zoomed.y + zoomed.height * point.y - cursor.y) < 1)
  assert.equal(await page.evaluate(() => scrollY), 0)
  await page.mouse.down()
  await page.mouse.move(cursor.x + 110, cursor.y - 70, { steps: 10 })
  await page.mouse.up()
  const moved = await canvas.boundingBox()
  assert.ok(Math.abs(moved.x - zoomed.x - 110) < 1)
  assert.ok(Math.abs(moved.y - zoomed.y + 70) < 1)
  // Release outside the surface, then start another drag: no stuck pointer state.
  await page.mouse.down()
  await page.mouse.move(900, 700, { steps: 10 })
  await page.mouse.up()
  await page.getByRole("button", { name: "Encuadrar", exact: true }).click()
  assert.ok(Math.abs((await canvas.boundingBox()).width - before.width) < 1)
  await page.mouse.move(300, 300)
  await page.mouse.down()
  await page.mouse.move(330, 320, { steps: 5 })
  await page.mouse.up()
  assert.ok(Math.abs((await canvas.boundingBox()).x - before.x - 30) < 1)
})

test("PDF pages render independently and reopening releases the previous renderer", async (t) => {
  const page = await mount(t)
  await page.getByRole("button", { name: "Encuadrar", exact: true }).waitFor()
  const pixel = () =>
    page.locator("canvas").evaluate((canvas) => {
      const { data } = canvas
        .getContext("2d")
        .getImageData(
          Math.round(canvas.width / 4),
          Math.round(canvas.height / 2),
          1,
          1,
        )
      return Array.from(data)
    })
  assert.deepEqual(await pixel(), [255, 0, 0, 255])
  await page
    .getByRole("button", { name: "Página siguiente", exact: true })
    .click()
  await page.getByText("2 / 2", { exact: true }).waitFor()
  assert.deepEqual(await pixel(), [0, 0, 255, 255])
  await page.mouse.move(400, 300)
  await page.mouse.wheel(0, -180)
  await page.evaluate(() => window.viewer.unmount())
  await page.waitForFunction(() => !document.querySelector("canvas"))
  await page.evaluate(() => window.viewer.mount())
  await page.getByText("1 / 2", { exact: true }).waitFor()
  assert.deepEqual(await pixel(), [255, 0, 0, 255])
})

test("the correction rotates the sheet and its dimension marker together on each page", async (t) => {
  const page = await mount(t, "rotated")
  for (const [number, box, color] of [
    [1, [80 / 600, 140 / 400, 260 / 600, 320 / 400], [255, 0, 0]],
    // This sheet already has /Rotate 90 in the original PDF.
    [2, [80 / 400, 80 / 600, 260 / 400, 260 / 600], [0, 0, 255]],
  ]) {
    await page.evaluate(
      ({ number, box }) =>
        window.viewer.mount({
          id: "dimension",
          page: number,
          box,
        }),
      { number, box },
    )
    await page.getByText(`${number} / 2`, { exact: true }).waitFor()
    // The page indicator can change before PDF.js swaps the previous bitmap.
    await page.waitForFunction((portrait) => {
      const canvas = document.querySelector("canvas")
      return (
        canvas.style.visibility === "visible" &&
        canvas.height > canvas.width === portrait
      )
    }, number === 1)
    const result = await page.locator("canvas").evaluate((canvas) => {
      const marker = canvas.nextElementSibling.firstElementChild.style
      const centerX = parseFloat(marker.left) + parseFloat(marker.width) / 2
      const centerY = parseFloat(marker.top) + parseFloat(marker.height) / 2
      const rect = canvas.getBoundingClientRect()
      const x = Math.round(((centerX - rect.left) / rect.width) * canvas.width)
      const y = Math.round(((centerY - rect.top) / rect.height) * canvas.height)
      const rgb = Array.from(
        canvas.getContext("2d").getImageData(x, y, 1, 1).data,
      ).slice(0, 3)
      return { rgb, centerX, centerY, portrait: rect.height > rect.width }
    })
    assert.deepEqual(result.rgb, color)
    assert.equal(result.portrait, number === 1)
    assert.ok(
      Math.abs(result.centerX - 400) < 1 && Math.abs(result.centerY - 300) < 1,
    )
  }
})

test("3D follows screen-space drag, crosses the poles, and stops when released", async (t) => {
  const page = await mount(t, "model")
  const initial = await page.evaluate(() => window.viewer.position())
  const drag = async (dx, dy, button = "middle") => {
    await page.mouse.move(400, 300)
    await page.mouse.down({ button })
    await page.mouse.move(400 + dx, 300 + dy, { steps: 20 })
    await page.mouse.up({ button })
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        ),
    )
  }
  await drag(90, 0, "left")
  assert.deepEqual(await page.evaluate(() => window.viewer.position()), initial)
  await drag(90, 0)
  assert.ok(
    (await page.evaluate(() => window.viewer.front()))[0] > 0,
    "grabbed front point follows drag to the right",
  )
  await page.evaluate(() => window.viewer.reset())
  await drag(0, 90)
  assert.ok(
    (await page.evaluate(() => window.viewer.front()))[1] < 0,
    "grabbed front point follows drag down",
  )
  let previous = await page.evaluate(() => window.viewer.position())
  for (let i = 0; i < 10; i++) {
    await drag(0, -260)
    const current = await page.evaluate(() => window.viewer.position())
    assert.ok(
      Math.hypot(...current.map((n, index) => n - previous[index])) > 0.1,
      "no pole lock",
    )
    previous = current
  }
  await page.waitForTimeout(250)
  assert.deepEqual(
    await page.evaluate(() => window.viewer.position()),
    previous,
  )
  await page.evaluate(() => window.viewer.reset())
  const reset = await page.evaluate(() => window.viewer.position())
  assert.ok(Math.hypot(...reset.map((n, i) => n - initial[i])) < 1e-8)
  await page.mouse.move(600, 300)
  await page.evaluate(() => {
    window.readAnchor = window.viewer.pointAtCursor()
  })
  await page.mouse.wheel(0, -180)
  await page.waitForFunction(() => window.viewer.zoom() > 1)
  assert.ok(
    Math.abs((await page.evaluate(() => window.readAnchor())) - 0.5) < 0.005,
    "wheel zoom anchors the point under the cursor",
  )
  const beforePan = await page.evaluate(() => window.viewer.target())
  const zoom = await page.evaluate(() => window.viewer.zoom())
  await page.keyboard.down("Control")
  await drag(65, 35)
  await page.keyboard.up("Control")
  assert.notDeepEqual(
    await page.evaluate(() => window.viewer.target()),
    beforePan,
  )
  assert.equal(await page.evaluate(() => window.viewer.zoom()), zoom)
  const center = await page.evaluate(() => window.viewer.projectedPivot())
  await drag(-45, 55)
  const rotated = await page.evaluate(() => window.viewer.projectedPivot())
  assert.ok(Math.hypot(...center.map((n, i) => n - rotated[i])) < 1e-7)
  const [live, restored] = await page.evaluate(() => [
    window.viewer.front(),
    window.viewer.restoredView(),
  ])
  assert.ok(
    Math.hypot(...live.map((n, i) => n - restored[i])) < 1e-6,
    "saved framing restores a rotated, panned and zoomed CAD",
  )
  await page.mouse.wheel(0, 180)
  await page.waitForFunction((zoom) => window.viewer.zoom() < zoom, zoom)
})

test("classic drag, perspective and inverted wheel are independent", async (t) => {
  const page = await mount(t, "model")
  await page.evaluate(() =>
    window.viewer.configure({
      cad_projection: "perspective",
      cad_controls: "classic",
      invert_zoom: true,
    }),
  )
  const [near, far] = await page.evaluate(() => window.viewer.parallel())
  assert.ok(Math.abs(near / far - 3) < 1e-8)
  const initial = await page.evaluate(() => window.viewer.position())
  await page.mouse.move(400, 300)
  await page.mouse.down()
  await page.mouse.move(465, 325, { steps: 10 })
  await page.mouse.up()
  const after = await page.evaluate(() => window.viewer.position())
  assert.ok(Math.hypot(...initial.map((n, i) => n - after[i])) > 1)
  await page.mouse.wheel(0, 180)
  await page.waitForFunction(() => window.viewer.zoom() > 1)
  await page.evaluate(() =>
    window.viewer.configure({
      cad_projection: "orthographic",
      cad_controls: "classic",
      invert_zoom: true,
    }),
  )
  const [a, b] = await page.evaluate(() => window.viewer.parallel())
  assert.ok(Math.abs(a - b) < 1e-8)
})

test("off-center legacy views keep their scale and orbit the solid in place", async (t) => {
  const page = await mount(t, "model")
  const results = await page.evaluate(() => [
    window.viewer.meshCenter(true),
    window.viewer.meshCenter(false),
    window.viewer.parallel(),
  ])
  assert.deepEqual(results[0], [2.75, 0.5, 5.25])
  assert.deepEqual(results[1], [3.5, 2, 7.5])
  assert.ok(Math.abs(results[2][0] - results[2][1]) < 1e-8)
  // Pockets on 3056 and 3167: the saved detail and the whole-piece pivot differ.
  for (const { size, pivot, ...saved } of [
    {
      size: 90.678,
      pivot: [1.765, 0.451, -2.521],
      position: [30.08, -28.24, 23.88],
      target: [-0.9, -10.08, -30.77],
      up: [-0.266, 0.406, 0.875],
    },
    {
      size: 123.294,
      pivot: [0, 0, 0],
      position: [-22.66, -42.23, 31.51],
      target: [-3.8, -34.65, -10.84],
      up: [0.227, 0.613, 0.757],
    },
  ]) {
    await page.evaluate(
      ({ size, pivot, saved }) => window.viewer.open(size, pivot, saved),
      { size, pivot, saved },
    )
    const height = await page.evaluate(() => window.viewer.height())
    const distance = Math.hypot(
      ...saved.position.map((x, i) => x - saved.target[i]),
    )
    assert.ok(Math.abs(height - 2 * Math.tan(Math.PI / 8) * distance) < 1e-7)
    const initial = await page.evaluate(() => window.viewer.projectedPivot())
    const initialCamera = await page.evaluate(() => window.viewer.position())
    await page.mouse.move(410, 320)
    await page.mouse.down({ button: "middle" })
    for (const [x, y] of [
      [410, 320],
      [445, 365],
      [480, 350],
    ]) {
      await page.mouse.move(x, y, { steps: 6 })
      const current = await page.evaluate(() => window.viewer.projectedPivot())
      assert.ok(Math.hypot(...current.map((n, i) => n - initial[i])) < 1e-7)
    }
    await page.mouse.up({ button: "middle" })
    const finalCamera = await page.evaluate(() => window.viewer.position())
    assert.ok(
      Math.hypot(...initialCamera.map((n, i) => n - finalCamera[i])) > 1,
    )
  }
})
