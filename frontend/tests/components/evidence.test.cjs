const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")
const result = buildSync({
  entryPoints: [
    path.resolve(
      __dirname,
      "../../src/components/Features/drawingSearchHelpers.ts",
    ),
  ],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
})
const moduleExports = { exports: {} }
new Function("module", "exports", result.outputFiles[0].text)(
  moduleExports,
  moduleExports.exports,
)
const { normalizeCota, matchesCota, matchesCotaPrefix } = moduleExports.exports

test("drawing numbers do not confuse N170 with N1700 or N17", () => {
  assert.equal(matchesCota("N1700", "N170", true), false)
  assert.equal(matchesCota("N170", "N17", true), false)
  assert.equal(matchesCota("N170", "N170", false), true)
})
test("subdimensions are included only when explicitly enabled", () => {
  assert.equal(matchesCota("N170.1", "N170", true), true)
  assert.equal(matchesCota("N170.1", "N170", false), false)
  assert.equal(matchesCota("N170.13", "N170.1", true), false)
})
test("user input accepts numbers, N prefixes, spaces and zero padding", () => {
  for (const input of ["170", "n170", " N 170 ", "00170"])
    assert.equal(normalizeCota(input), "N170")
  assert.equal(normalizeCota("170.1"), "N170.1")
  assert.equal(normalizeCota(""), "")
  assert.equal(normalizeCota("940.1"), "N940.1")
})

test("search suggestions accept partial numbers without changing exact number matching", () => {
  for (const query of ["N1", "N11", "11", "n 0011"])
    assert.equal(matchesCotaPrefix("N113", query), true)
  assert.equal(matchesCotaPrefix("N170.5", "170"), true)
  assert.equal(matchesCotaPrefix("N113", "N12"), false)
})
