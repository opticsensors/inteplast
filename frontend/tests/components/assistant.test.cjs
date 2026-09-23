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
    entryPoints: [path.join(__dirname, "fixtures/assistant.jsx")],
    bundle: true,
    write: false,
    format: "iife",
    platform: "browser",
    jsx: "automatic",
    tsconfig: path.join(frontend, "tsconfig.json"),
    define: { "process.env.NODE_ENV": '"development"' },
  })
  bundle = result.outputFiles[0].text
  browser = await chromium.launch({ headless: true })
})
after(async () => browser?.close())

async function mount(t) {
  const page = await browser.newPage()
  page.setDefaultTimeout(5000)
  t.after(() => page.close())
  await page.route("**/*", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: '<html><body><div id="root"></div></body></html>',
    }),
  )
  await page.goto("http://component.invalid/")
  await page.addScriptTag({ content: bundle })
  await page.getByRole("button", { name: "Asistente", exact: true }).click()
  return page
}
async function ask(page, question) {
  await page
    .getByRole("textbox", { name: "Pregunta al asistente" })
    .fill(question)
  await page.getByRole("button", { name: "Enviar pregunta" }).click()
  await expect(
    page.getByRole("button", { name: "Detener respuesta" }),
  ).toBeVisible()
}
async function reply(page, text = "Medición: 3,95 mm. ✅") {
  await page.evaluate(
    (text) =>
      window.assistantEmit([
        { type: "delta", text },
        {
          type: "sources",
          sources: [
            {
              label: "Pieza 3212",
              url: "/parts/11111111-1111-1111-1111-111111111111?revision=06",
            },
            { label: "Untrusted", url: "javascript:alert(1)" },
          ],
        },
        { type: "done", truncated: false },
      ]),
    text,
  )
  await expect(page.getByText("Respuesta completada.")).toBeVisible()
}

test("streams split UTF-8 safely and keeps history without sending page context after navigation", async (t) => {
  const page = await mount(t)
  await ask(page, "Lee N170")
  await reply(page)
  await expect(page.getByText("Medición: 3,95 mm. ✅")).toBeVisible()
  await expect(page.getByRole("link", { name: "Untrusted" })).toHaveCount(0)
  await expect(page.getByRole("link", { name: "Pieza 3212" })).toHaveCount(1)
  await page
    .getByRole("button", { name: "Minimizar chat", exact: true })
    .click()
  await expect(page.getByRole("textbox")).toHaveCount(0)
  await page.getByRole("button", { name: "Expandir chat", exact: true }).click()
  await expect(page.getByText("Medición: 3,95 mm. ✅")).toBeVisible()
  await page.evaluate(() =>
    window.assistantNavigate(
      "/parts/22222222-2222-2222-2222-222222222222?revision=07&cota=N999",
    ),
  )
  await ask(page, "Consulta la pieza 3212")
  const requests = await page.evaluate(() => window.assistantRequests)
  assert.equal("context" in requests[1], false)
  assert.equal(JSON.stringify(requests[1]).includes("22222222"), false)
  assert.equal(JSON.stringify(requests[1]).includes("N999"), false)
  assert.equal(requests[1].messages.length, 3)
  await reply(page, "No hay medidas importadas para esa revisión.")
  await page.getByRole("button", { name: "Cerrar asistente" }).click()
  await page.getByRole("button", { name: "Asistente", exact: true }).click()
  await expect(
    page.getByText("No hay medidas importadas para esa revisión."),
  ).toBeVisible()
})

test("stop excludes partial answers from later history and reset clears the conversation", async (t) => {
  const page = await mount(t)
  await ask(page, "Primera")
  await page.evaluate(() =>
    window.assistantEmit([{ type: "delta", text: "Parcial" }], false),
  )
  await page.getByRole("button", { name: "Detener respuesta" }).click()
  await expect(page.getByRole("alert")).toHaveText("Respuesta detenida.")
  await ask(page, "Segunda")
  const requests = await page.evaluate(() => window.assistantRequests)
  assert.deepEqual(requests[1].messages, [{ role: "user", content: "Segunda" }])
  await page.getByRole("button", { name: "Nueva conversación" }).click()
  await expect(
    page.getByText(
      "Consulta el conocimiento de Inteplast, pregunta por piezas, features, notas, mediciones o retoques.",
    ),
  ).toBeVisible()
  await expect(page.getByText("Parcial", { exact: true })).toHaveCount(0)
  await ask(page, "Tercera")
  await reply(page, "Nueva respuesta")
})

test("shows provider errors and retries the question without duplicate history", async (t) => {
  const page = await mount(t)
  await ask(page, "Consulta")
  await page.evaluate(() =>
    window.assistantEmit([
      { type: "error", text: "No se puede conectar con Ollama." },
    ]),
  )
  await expect(page.getByRole("alert")).toHaveText(
    "No se puede conectar con Ollama.",
  )
  await page.getByRole("button", { name: "Volver a intentar" }).click()
  await reply(page, "Conexión recuperada.")
  await expect(page.getByText("Consulta", { exact: true })).toHaveCount(1)
  const requests = await page.evaluate(() => window.assistantRequests)
  assert.equal(requests[1].messages.length, 1)
})

test("detects a cut stream instead of marking an incomplete answer as successful", async (t) => {
  const page = await mount(t)
  await ask(page, "Consulta")
  await page.evaluate(() =>
    window.assistantEmit([{ type: "delta", text: "Incompleta" }]),
  )
  await expect(page.getByRole("alert")).toContainText("Se ha interrumpido")
  await expect(page.getByText("Respuesta completada.")).toHaveCount(0)
})

test("long answers stay visible and retain the previous question in follow-up history", async (t) => {
  const page = await mount(t)
  await ask(page, "Detalla N170 de la pieza 3212")
  const answer = `${"Dato completo. ".repeat(300)}FINAL VISIBLE`
  await reply(page, answer)
  await expect(page.getByText(answer)).toBeVisible()
  await ask(page, "¿Y la cavidad c16?")
  const requests = await page.evaluate(() => window.assistantRequests)
  assert.equal(requests[1].messages.length, 3)
  assert.equal(requests[1].messages[0].content, "Detalla N170 de la pieza 3212")
  assert.ok(requests[1].messages[1].content.length <= 3000)
  assert.match(requests[1].messages[1].content, /abreviada en el historial/)
})
