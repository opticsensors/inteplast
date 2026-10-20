const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [
    path.resolve(
      __dirname,
      "../../src/components/Parts/measurementSelection.ts",
    ),
  ],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  tsconfig: path.resolve(__dirname, "../../tsconfig.json"),
})
const compiled = { exports: {} }
new Function("module", "exports", result.outputFiles[0].text)(
  compiled,
  compiled.exports,
)
const { describeSeries } = compiled.exports

const entry = (id) => ({
  id,
  numbers: [id],
  kind: "dimension",
  title: id,
  series: [],
  actions: [],
  reviewed_case: null,
})
// The XLS reader stores Equipment and type as empty strings when the cells are blank.
const report = (code, nominal, idx, element = "", evaluation = "") => {
  const title = `${code} ${nominal} ${evaluation}`.trim()
  return {
    id: `PPAP:DR(3D):${code}:${idx}`,
    label: title,
    block: title,
    idx,
    unit: "mm",
    element,
    evaluation,
    records: {},
  }
}

test("report rows without Equipment or type are never described with pilot rules", () => {
  const diameter = describeSeries(entry("N161"), report("N161", 45.4, 1))
  assert.deepEqual(
    {
      element: diameter.element,
      label: diameter.label,
      variant: diameter.variant,
      comparisonIndex: diameter.comparisonIndex,
    },
    {
      element: "Equipo no indicado",
      label: "N161 45.4 · 1",
      variant: undefined,
      comparisonIndex: undefined,
    },
  )
  const thickness = describeSeries(entry("N165"), report("N165", 1.35, 2))
  assert.equal(thickness.label, "N165 1.35 · 2")
  assert.notEqual(thickness.label, "Máximo")
  assert.equal(thickness.variant, undefined)
  const distance = describeSeries(entry("N240"), report("N240", 18.5, 1))
  assert.equal(distance.element, "Equipo no indicado")
  assert.equal(distance.variant, undefined)
})

test("report rows keep the columns they do provide", () => {
  const onlyEquipment = describeSeries(
    entry("N161"),
    report("N161", 45.4, 1, "CMM"),
  )
  assert.equal(onlyEquipment.element, "CMM")
  assert.equal(onlyEquipment.label, "N161 45.4 · 1")
  const onlyType = describeSeries(
    entry("N161"),
    report("N161", 45.4, 2, "", "LP(2) MAX."),
  )
  assert.equal(onlyType.element, "Equipo no indicado")
  assert.equal(onlyType.label, "LP(2) MAX.")
  const complete = describeSeries(
    entry("N161"),
    report("N161", 45.4, 1, "CMM", "GX"),
  )
  assert.deepEqual([complete.element, complete.label], ["CMM", "GX"])
  assert.equal(complete.metric, "PPAP:DR(3D):N161:1")
})

test("pilot CMM series keep their reviewed identities", () => {
  const bolt = describeSeries(entry("N170"), {
    id: "N170|B2-H5.0|2",
    label: "B2-H5.0 · LP máximo",
    unit: "mm",
    records: {},
  })
  assert.deepEqual(
    [bolt.element, bolt.height, bolt.label, bolt.variant, bolt.comparisonIndex],
    ["B2", "5.0", "LP máximo", "B2-H5.0", 1],
  )
  const diameter = describeSeries(entry("N161"), {
    id: "N161 DIAM. 45.4|1|1",
    label: "N161 DIAM. 45.4 · [1] Diámetro",
    block: "N161 DIAM. 45.4",
    idx: 1,
    unit: "mm",
    records: {},
  })
  assert.deepEqual(
    [diameter.element, diameter.label, diameter.variant],
    ["Diámetro", "GX", "main"],
  )
  const global = describeSeries(entry("N165"), {
    id: "GLOBAL MIN/MAX|1|2",
    label: "GLOBAL MIN/MAX · [2] Cálculo de fórmula",
    block: "GLOBAL MIN/MAX",
    idx: 2,
    unit: "mm",
    records: {},
  })
  assert.deepEqual(
    [global.element, global.label, global.comparisonIndex],
    ["GLOBAL", "Máximo", 1],
  )
})

test("generic CMM exports from other pieces keep element and evaluation", () => {
  const generic = describeSeries(entry("N230"), {
    id: "N230 DIAMETRO|1|1|CMM:21",
    label: "N230 DIAMETRO · [1] Diámetro",
    block: "N230 DIAMETRO",
    idx: 1,
    unit: "mm",
    element: "CMM 21",
    evaluation: "Diámetro · 1",
    records: {},
  })
  assert.deepEqual(
    [generic.element, generic.label, generic.metric],
    ["CMM 21", "Diámetro · 1", "N230 DIAMETRO|1|1|CMM:21"],
  )
})
