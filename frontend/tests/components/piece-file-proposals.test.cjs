const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")

const result = buildSync({
  entryPoints: [
    path.resolve(__dirname, "../../src/components/Parts/pieceFileDrafts.ts"),
  ],
  bundle: true,
  write: false,
  platform: "node",
  format: "cjs",
  tsconfig: path.resolve(__dirname, "../../tsconfig.json"),
})
const compiled = { exports: {} }
new Function("module", "exports", "require", result.outputFiles[0].text)(
  compiled,
  compiled.exports,
  require,
)
const { discoveredFiles } = compiled.exports

test("all drawing candidates are proposed, with one chosen primary and no duplication", () => {
  const files = discoveredFiles({
    references: [
      {
        kind: "drawing",
        path: "9000/tapa.pdf",
        source_version: "v2",
        candidates: [
          { path: "9000/base.pdf", source_version: "v1" },
          { path: "9000/tapa.pdf", source_version: "v2" },
        ],
      },
      {
        kind: "part",
        path: "9000/part.step",
        candidates: [{ path: "9000/other.step" }],
      },
    ],
  })
  assert.deepEqual(
    files.filter((f) => f.kind === "drawing").map((f) => [f.path, f.primary]),
    [
      ["9000/tapa.pdf", true],
      ["9000/base.pdf", false],
    ],
  )
  assert.equal(files.filter((f) => f.kind === "part").length, 1)
})

test("explicitly removed drawings are not restored from candidates", () => {
  assert.deepEqual(
    discoveredFiles({
      references: [
        {
          kind: "drawing",
          path: null,
          candidates: [{ path: "9000/base.pdf" }],
        },
      ],
    }),
    [],
  )
})
