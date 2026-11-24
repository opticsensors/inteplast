const assert = require("node:assert/strict")
const path = require("node:path")
const { test } = require("node:test")
const { buildSync } = require("esbuild")
const { chromium } = require("playwright")

test("shaded CAD shows a tangent face join, hides rear edges and omits triangle diagonals", async (t) => {
  const bundle = buildSync({
    stdin: {
      resolveDir: path.resolve(__dirname, "../../src/components/Features"),
      contents: `
        import * as THREE from "three"
        import { addCadEdges } from "./cadEdges"
        import { cadBoundaryIndices } from "./coverFaceRanges"
        const renderer = new THREE.WebGLRenderer({ antialias: false })
        renderer.setSize(160, 160)
        const scene = new THREE.Scene()
        const camera = new THREE.OrthographicCamera(-2, 2, 2, -2, 0.1, 10)
        camera.position.z = 4
        const geometry = new THREE.BufferGeometry()
        geometry.setAttribute("position", new THREE.Float32BufferAttribute([
          -1.5,-1,0, 0,-1,0, 0,1,0, -1.5,1,0, 1.5,-1,0, 1.5,1,0
        ], 3))
        geometry.setIndex([0,1,2, 0,2,3, 1,4,5, 1,5,2])
        const surface = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial())
        const outline = addCadEdges(surface, cadBoundaryIndices(geometry.index.array, 6, [{first:0,last:1}, {first:2,last:3}]))
        const rear = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial())
        rear.position.z = -0.5
        addCadEdges(rear)
        scene.add(surface, rear)
        renderer.render(scene, camera)
        const gl = renderer.getContext()
        const pixels = new Uint8Array(160 * 160 * 4)
        gl.readPixels(0, 0, 160, 160, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
        function darkest(x, y) {
          return Math.min(...[-1, 0, 1].flatMap(dx => [-1, 0, 1].map(dy =>
            pixels[((y+dy)*160 + x+dx)*4])))
        }
        window.sample = {
          segments: outline.geometry.index.count / 2,
          tangent: darkest(80, 80), outer: darkest(20, 80),
          diagonal: darkest(50, 80), behind: darkest(100, 80)
        }
        renderer.dispose()
      `,
    },
    bundle: true,
    write: false,
    platform: "browser",
  }).outputFiles[0].text
  const browser = await chromium.launch()
  t.after(() => browser.close())
  const page = await browser.newPage()
  await page.addScriptTag({ content: bundle })
  const sample = await page.evaluate(() => window.sample)
  assert.equal(sample.segments, 8)
  assert.ok(sample.tangent < 90 && sample.outer < 90, JSON.stringify(sample))
  assert.ok(
    sample.diagonal > 230 && sample.behind > 230,
    JSON.stringify(sample),
  )
})
