const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { transformSync } = require("esbuild")
const { readFileSync } = require("node:fs")

const source = readFileSync(
  path.join(__dirname, "../../src/components/Features/coverFaceRanges.ts"),
  "utf8",
)
const { code } = transformSync(source, { loader: "ts", format: "cjs" })
const compiled = { exports: {} }
new Function("module", code)(compiled)
const { coverFaceRanges } = compiled.exports

test("empty OCCT faces preserve the original indices of selectable faces", () => {
  const faces = [
    { first: 0, last: -1 },
    { first: 0, last: 3 },
    { first: 4, last: 3 },
    { first: 4, last: 5 },
    { first: 6, last: 5 },
  ]
  assert.deepEqual(coverFaceRanges(faces, 6), [
    { first: 0, last: 3, faceIndex: 1 },
    { first: 4, last: 5, faceIndex: 3 },
  ])
  for (const bad of [
    { first: 3, last: 4 },
    { first: 4, last: 2 },
    { first: 4, last: 6 },
  ])
    assert.throws(() => coverFaceRanges([faces[1], bad], 6), /superficies/)
})
