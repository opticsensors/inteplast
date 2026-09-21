const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [
    path.resolve(
      __dirname,
      "../../src/components/Parts/consultationEntries.ts",
    ),
  ],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
})
const compiled = { exports: {} }
new Function("module", "exports", result.outputFiles[0].text)(
  compiled,
  compiled.exports,
)
const { consultationEntries } = compiled.exports
const cota = (code, revision = "06") => ({ code, revision, title: code })
const measure = (id, numbers = [id]) => ({
  id,
  numbers,
  series: [{ id: "measured" }],
  actions: [],
})
const study = {
  measurement_revision: "06",
  catalog: {
    entries: [
      measure("N170"),
      measure("N117 / N118", ["N117", "N118"]),
      measure("N240"),
      { ...measure("coordinates-1"), kind: "diagnostic", title: "Coordenadas" },
      { ...measure("coordinates-2"), kind: "diagnostic", title: "Coordenadas" },
    ],
  },
}

test("feature scope uses actual links, including unmeasured cotas and one number of a joint evaluation", () => {
  const feature = {
    characteristics: [cota("N170"), cota("N117"), cota("N288")],
  }
  const entries = consultationEntries(study, [cota("N240")], feature)
  assert.deepEqual(
    entries.map((entry) => entry.id),
    ["N170", "N117", "N288"],
  )
  assert.deepEqual(entries[1].numbers, ["N117"])
  assert.equal(entries[1].series.length, 1)
  assert.deepEqual(entries[2].series, [])
  assert.deepEqual(consultationEntries(study, [], { characteristics: [] }), [])
  assert.deepEqual(consultationEntries(study, [], null), [])
})

test("a feature's older revision cannot inherit measurements from the current snapshot", () => {
  const feature = { characteristics: [cota("N170", "04")] }
  const [entry] = consultationEntries(study, [], feature)
  assert.equal(entry.revision, "04")
  assert.deepEqual(entry.series, [])
  const entries = consultationEntries(study, [], {
    characteristics: [cota("N170", "04"), cota("N170")],
  })
  assert.equal(entries.length, 1)
  assert.equal(entries[0].revision, "06")
  assert.equal(entries[0].series.length, 1)
})

test("whole-piece consultation retains unassigned and unmeasured cotas even before import", () => {
  const entries = consultationEntries(
    study,
    [cota("N170"), cota("N288")],
    undefined,
  )
  assert.deepEqual(
    entries.map((entry) => entry.id),
    ["N117 / N118", "N170", "N240", "N288"],
  )
  assert.equal(entries.find((entry) => entry.id === "N240").series.length, 1)
  const pending = consultationEntries(undefined, [cota("N288")], undefined)
  assert.equal(pending[0].id, "N288")
  assert.deepEqual(pending[0].series, [])
})
