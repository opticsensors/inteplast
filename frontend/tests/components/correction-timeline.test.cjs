const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [
    path.resolve(__dirname, "../../src/components/Parts/correctionTimeline.ts"),
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
const { correctionTimeline, intervalValues } = compiled.exports

function fixture() {
  const item = { xls_before: 10, prediction: 10.5, steps: [{ delta: 0.5 }] }
  const study = {
    samples: ["01", "03", "05", "08"],
    corrections: {
      1: { before: "01", after: "03", date: "date1" },
      2: { before: "03", after: "05", date: "date2" },
    },
    cases: {
      N170: {
        correction: "1",
        actions: ["1.33"],
        description: "Propuesta",
        comparisons: { "B1-H1.5": { c13: { items: [item] } } },
      },
    },
    actions: {
      1.33: {
        id: "1.33",
        images: [{ url: "diagram1" }],
        paragraphs: ["Propuesta1"],
      },
    },
    action_index: {
      1.33: {
        id: "1.33",
        plan: "1",
        images: [{ url: "logo" }, { url: "diagram1" }],
      },
      2.7: {
        id: "2.7",
        plan: "2",
        images: [{ url: "logo" }, { url: "diagram2" }],
        paragraphs: ["Propuesta2"],
      },
    },
  }
  const entry = { reviewed_case: "N170", actions: ["1.33", "2.7"] }
  const evaluation = {
    variant: "B1-H1.5",
    comparisonIndex: 0,
    series: {
      records: {
        c13: {
          "01": { value: 10.1 },
          "03": { value: 10.6 },
          "05": { value: 11.2 },
          "08": { value: 12 },
        },
      },
    },
  }
  return { study, entry, evaluation }
}

test("all intervals retain linked plans without inferring a retouch from a measurement jump", () => {
  const { study, entry, evaluation } = fixture()
  const intervals = correctionTimeline(study, entry, evaluation)
  assert.deepEqual(
    intervals.map((interval) => interval.actions.map((action) => action.id)),
    [["1.33"], ["2.7"], []],
  )
  assert.deepEqual(
    intervals.map((interval) => Boolean(interval.comparison)),
    [true, false, false],
  )
  assert.deepEqual(intervals[1].actions[0].images, [{ url: "diagram2" }])
  assert.equal(
    intervalValues(intervals[2], evaluation, "c13").expectedChange,
    null,
  )
})

test("predicted change uses the XLS baseline separately from the CSV baseline", () => {
  const { study, entry, evaluation } = fixture()
  const interval = correctionTimeline(study, entry, evaluation)[0]
  const result = intervalValues(interval, evaluation, "c13")
  assert.equal(result.expectedChange, 0.5)
  assert.equal(result.measuredChange, 0.5)
  assert.notEqual(
    result.expectedChange,
    result.comparison.prediction - result.before.value,
  )
})

test("unmapped evaluations keep actions but never inherit another evaluation's prediction", () => {
  const { study, entry, evaluation } = fixture()
  delete evaluation.variant
  const interval = correctionTimeline(study, entry, evaluation)[0]
  assert.equal(interval.actions[0].id, "1.33")
  assert.equal(interval.comparison, undefined)
  assert.equal(intervalValues(interval, evaluation, "c13").expectedChange, null)
})

test("zero is measured; missing and non-finite measurements never become a zero change", () => {
  const { study, entry, evaluation } = fixture()
  const interval = correctionTimeline(study, entry, evaluation)[0]
  const records = evaluation.series.records.c13
  records["01"].value = 0
  records["03"].value = 0
  assert.equal(intervalValues(interval, evaluation, "c13").measuredChange, 0)
  for (const missing of [null, undefined, Number.NaN]) {
    records["03"].value = missing
    assert.equal(
      intervalValues(interval, evaluation, "c13").measuredChange,
      null,
    )
  }
})
