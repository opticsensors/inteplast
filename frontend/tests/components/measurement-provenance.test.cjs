const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const React = require("react")
const { renderToStaticMarkup } = require("react-dom/server")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [
    path.resolve(__dirname, "../../src/components/Parts/MeasurementPlot.tsx"),
  ],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  jsx: "automatic",
  external: ["react", "react/*", "react-dom", "react-dom/*"],
  tsconfig: path.resolve(__dirname, "../../tsconfig.json"),
})
const compiled = { exports: {} }
new Function("module", "exports", "require", result.outputFiles[0].text)(
  compiled,
  compiled.exports,
  require,
)
const { MeasurementPlot } = compiled.exports

test("dense histories thin axis labels while keeping every point accessible", () => {
  const labels = Array.from(
    { length: 92 },
    (_, i) => `intern.${i + 1}.muestra5`,
  )
  const html = renderToStaticMarkup(
    React.createElement(MeasurementPlot, {
      labels,
      visible: ["c1"],
      lines: [{ name: "c1", points: labels.map((_, i) => ({ value: i })) }],
    }),
  )
  const ticks = html.match(/<text[^>]* y="263"[^>]*>[\s\S]*?<\/text>/g)
  assert.ok(ticks.length > 1 && ticks.length < labels.length)
  assert.match(ticks[0], />1\.muestra5</)
  assert.match(ticks.at(-1), />92\.muestra5</)
  assert.equal((html.match(/<circle /g) ?? []).length, labels.length)
  for (const label of labels)
    assert.ok(html.includes(`Consultar C1 · ${label}`))
})

test("the chart shows only usable measurements and leaves import diagnostics out of the view", () => {
  const html = renderToStaticMarkup(
    React.createElement(MeasurementPlot, {
      labels: ["01", "02", "03"],
      visible: ["c1"],
      lines: [
        {
          name: "c1",
          points: [
            {
              value: 2,
              provenance_state: "medicion",
              warnings: ["Revisar cabecera."],
            },
            { value: 777, provenance_state: "generado", flags: ["aleatoria"] },
            { value: 999, provenance_state: "sin_confirmar" },
          ],
        },
      ],
    }),
  )
  assert.doesNotMatch(html, /valores excluidos|>777<|>999<|Revisar cabecera/)
  const svg = html.match(/<svg[\s\S]*?<\/svg>/)[0]
  assert.equal((svg.match(/<circle /g) || []).length, 1)
})

test("copied measurements are never plotted twice", () => {
  const html = renderToStaticMarkup(
    React.createElement(MeasurementPlot, {
      labels: ["01", "02"],
      visible: ["c1"],
      lines: [
        {
          name: "c1",
          points: [
            { value: 2, provenance_state: "medicion" },
            {
              value: 2,
              provenance_state: "medicion",
              flags: ["copia"],
              duplicate_of: { sheet: "DR", cell: "I15" },
            },
          ],
        },
      ],
    }),
  )
  assert.doesNotMatch(html, /valores excluidos|DR!I15/)
  assert.equal((html.match(/<circle /g) || []).length, 1)
})
