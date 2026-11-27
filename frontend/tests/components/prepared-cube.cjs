const fs = require("node:fs")
const path = require("node:path")
const { execFileSync } = require("node:child_process")
const esbuild = require("esbuild")

// Exercise the same STEP-to-GLB converter as the server with a real six-face solid.
module.exports = function preparedCube(dir) {
  const occt = path.dirname(require.resolve("occt-import-js/package.json"))
  fs.mkdirSync(dir, { recursive: true })
  const script = path.join(dir, "cover.cjs")
  const glb = path.join(dir, "cube.glb")
  esbuild.buildSync({
    entryPoints: [
      path.resolve(__dirname, "../../../backend/scripts/cover-glb.mjs"),
    ],
    outfile: script,
    bundle: true,
    platform: "node",
    format: "cjs",
    external: ["occt-import-js"],
  })
  execFileSync(
    process.execPath,
    [script, path.join(occt, "test/testfiles/simple-basic-cube/cube.stp"), glb],
    {
      env: { ...process.env, NODE_PATH: path.dirname(occt) },
    },
  )
  return glb
}
