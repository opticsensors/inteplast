const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [
    path.resolve(__dirname, "../../src/components/Parts/sourceTableHelpers.ts"),
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
const { sourcePosition, searchCells } = compiled.exports

test("legacy repeated CMM headers resolve the saved occurrence and row", () => {
  const row = (value) => ["16", "GX", "", "4", "0", "-0.1", value, ""]
  const sheets = [
    {
      name: "CSV",
      rows: [
        ["N170 BOLT 1"],
        row("3.970"),
        [""],
        ["N170 BOLT 1"],
        row("3.975"),
        ["", "LP", "", "4", "0", "-0.1", "4.025", ""],
      ],
    },
  ]
  assert.deepEqual(
    sourcePosition(
      sheets,
      "N170 BOLT 1 · aparición 2 · fila 2 · CMM 16",
      "c13",
      "4.025",
    ),
    { sheet: 0, row: 5, column: 6 },
  )
  assert.equal(
    sourcePosition(sheets, "N170 BOLT 1 · aparición 3 · fila 2 · CMM 16"),
    undefined,
  )
})

test("comparative CSV values keep their cavity column, including zero and decimal commas", () => {
  const sheets = [
    {
      name: "CSV",
      rows: [
        ["N170", "", "", "", "", "c1", "c2"],
        ["16", "GX", "", "4", "", "0", "3,975"],
      ],
    },
  ]
  assert.deepEqual(sourcePosition(sheets, "Línea 2 · N170", "c1", "0"), {
    sheet: 0,
    row: 1,
    column: 5,
  })
  assert.deepEqual(sourcePosition(sheets, "Línea 2 · N170", "c2", "3.975"), {
    sheet: 0,
    row: 1,
    column: 6,
  })
})

test("Excel addresses and searches retain sheet coordinates without interpreting HTML", () => {
  const sheets = [
    { name: "INTRO", rows: [["N170"]] },
    { name: "DR PAR", rows: [[], ["N170", "<script>raw</script>", "3.975"]] },
  ]
  assert.deepEqual(sourcePosition(sheets, "'DR PAR'!$C$2"), {
    sheet: 1,
    row: 1,
    column: 2,
  })
  assert.deepEqual(searchCells(sheets, "N170"), [
    { sheet: 0, row: 0, column: 0 },
    { sheet: 1, row: 1, column: 0 },
  ])
  assert.equal(searchCells(sheets, "inexistente").length, 0)
})
