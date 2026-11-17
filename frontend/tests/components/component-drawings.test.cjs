const assert = require("node:assert/strict")
const { test } = require("node:test")
const path = require("node:path")
const { buildSync } = require("esbuild")
const vm = require("node:vm")

const bundled = buildSync({
  entryPoints: [
    path.join(__dirname, "../../src/components/Parts/componentDrawings.ts"),
  ],
  bundle: true,
  platform: "node",
  format: "cjs",
  write: false,
}).outputFiles[0].text
const sandbox = { module: { exports: {} } }
vm.runInNewContext(bundled, sandbox)
const { componentDrawings, drawingNumber } = sandbox.module.exports

test("a number opens only its component and revision; ambiguous and unassigned plans have no fallback", () => {
  const data = {
    part: { folder_path: "project" },
    components: [
      {
        key: "BASE",
        files: [
          { path: "base.pdf", revision: "01" },
          { path: "base-v2.pdf", revision: "02" },
        ],
      },
      { key: "TAPA", files: [{ path: "cover.pdf", revision: "01" }] },
    ],
    documents: ["base.pdf", "base-v2.pdf", "cover.pdf"].map((filename) => ({
      id: filename,
      relative_path: `project/${filename}`,
    })),
  }
  assert.equal(componentDrawings(data, "BASE:N16", "01")[0].id, "base.pdf")
  assert.equal(componentDrawings(data, "TAPA:N16", "01")[0].id, "cover.pdf")
  assert.equal(componentDrawings(data, "BASE:N16", "02")[0].id, "base-v2.pdf")
  assert.equal(componentDrawings(data, "BASE:N16", "03").length, 0)
  assert.equal(componentDrawings(data, "N16", "01").length, 0)
  assert.equal(drawingNumber("TAPA:N16"), "N16")
  data.components[0].files.push({ path: "base-v2.pdf", revision: "01" })
  assert.equal(componentDrawings(data, "BASE:N16", "01").length, 2)
  assert.equal(
    componentDrawings({ ...data, components: [] }, "N16", "01"),
    undefined,
  )
})
