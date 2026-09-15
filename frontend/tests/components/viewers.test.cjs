const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const { before, after, test } = require("node:test")
const esbuild = require("esbuild")
const { chromium } = require("playwright")

const frontend = path.resolve(__dirname, "../..")
let browser, bundle, worker
// Two vector sheets with different colors. No customer files or external requests.
function syntheticPdf() {
  const stream = (color) => `${color} rg 80 80 180 180 re f`
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Resources << >> /Contents 4 0 R >>",
    `<< /Length ${stream("1 0 0").length} >>\nstream\n${stream("1 0 0")}\nendstream`,
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Resources << >> /Contents 6 0 R >>",
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
        body: syntheticPdf(),
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

test("3D follows screen-space drag, crosses the poles, and stops when released", async (t) => {
  const page = await mount(t, "model")
  const initial = await page.evaluate(() => window.viewer.position())
  const drag = async (dx, dy) => {
    await page.mouse.move(400, 300)
    await page.mouse.down()
    await page.mouse.move(400 + dx, 300 + dy, { steps: 20 })
    await page.mouse.up()
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        ),
    )
  }
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
  assert.deepEqual(await page.evaluate(() => window.viewer.position()), initial)
  await page.mouse.move(400, 300)
  await page.mouse.wheel(0, -180)
  await page.waitForFunction(
    (distance) => window.viewer.distance() < distance,
    Math.hypot(...initial),
  )
})
