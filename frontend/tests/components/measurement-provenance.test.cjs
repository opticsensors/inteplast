const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const React = require("react")
const { renderToStaticMarkup } = require("react-dom/server")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [path.resolve(__dirname, "../../src/components/Parts/MeasurementPlot.tsx")],
  bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic",
  external: ["react", "react/*", "react-dom", "react-dom/*"],
  tsconfig: path.resolve(__dirname, "../../tsconfig.json"),
})
const compiled = { exports: {} }
new Function("module", "exports", "require", result.outputFiles[0].text)(compiled, compiled.exports, require)
const { MeasurementPlot } = compiled.exports

test("excluded values remain visible as evidence but are never plotted as measurements", () => {
  const html = renderToStaticMarkup(React.createElement(MeasurementPlot, {
    labels: ["01", "02", "03"], visible: ["c1"],
    lines: [{ name: "c1", points: [
      { value: 2, provenance_state: "medicion" },
      { value: 777, provenance_state: "generado", flags: ["aleatoria"] },
      { value: 999, provenance_state: "sin_confirmar" },
    ] }],
  }))
  assert.match(html, /2 valores excluidos/)
  assert.match(html, /777/)
  assert.match(html, /999/)
  assert.match(html, /fórmula aleatoria/)
  assert.match(html, /Procedencia sin confirmar/)
  const svg = html.match(/<svg[\s\S]*?<\/svg>/)[0]
  assert.equal((svg.match(/<circle /g) || []).length, 1)
})

 test("copied measurements expose their origin without plotting twice", () => {
 const html = renderToStaticMarkup(React.createElement(MeasurementPlot, {
 labels:["01","02"], visible:["c1"], lines:[{name:"c1",points:[
 {value:2,provenance_state:"medicion"},
 {value:2,provenance_state:"medicion",flags:["copia"],duplicate_of:{sheet:"DR",cell:"I15"}}
 ]}]}))
 assert.match(html,/1 valores excluidos/)
 assert.match(html,/Copia de DR!I15/)
 assert.equal((html.match(/<circle /g)||[]).length,1)
 })
