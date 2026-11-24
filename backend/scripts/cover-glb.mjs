import fs from "node:fs"
import path from "node:path"
import { createHash } from "node:crypto"
import occtimportjs from "occt-import-js"
import { COVER_RECIPE } from "../../frontend/src/components/Features/cadCover"
import { prepareCoverGeometry } from "../../frontend/src/components/Features/prepareCoverGeometry"

// GLB 2.0 with one node per OCCT mesh. Ranges retain even empty B-rep faces,
// so the indices stored in existing annotations continue to address the same face.
async function convert(source, output) {
  const bytes = fs.readFileSync(source)
  const sourceHash = createHash("sha256").update(bytes).digest("hex")
  const occt = await occtimportjs()
  const { meshes, geometryKey } = await prepareCoverGeometry(
    occt.ReadStepFile(bytes, null),
  )
  const chunks = [],
    bufferViews = [],
    accessors = []
  let length = 0,
    triangles = 0
  function accessor(array, vector, target) {
    const count = array.length / (vector ? 3 : 1)
    const index = bufferViews.length
    bufferViews.push({
      buffer: 0,
      byteOffset: length,
      byteLength: array.byteLength,
      target,
    })
    chunks.push(Buffer.from(array.buffer, array.byteOffset, array.byteLength))
    length += array.byteLength
    accessors.push({
      bufferView: index,
      componentType: vector ? 5126 : 5125,
      count,
      type: vector ? "VEC3" : "SCALAR",
    })
    return index
  }
  const glMeshes = meshes.map((mesh) => {
    const position = accessor(mesh.positions, true, 34962)
    const min = [Infinity, Infinity, Infinity],
      max = [-Infinity, -Infinity, -Infinity]
    for (let i = 0; i < mesh.positions.length; i++) {
      const axis = i % 3,
        v = mesh.positions[i]
      min[axis] = Math.min(min[axis], v)
      max[axis] = Math.max(max[axis], v)
    }
    Object.assign(accessors[position], { min, max })
    const attributes = { POSITION: position }
    if (mesh.normals) attributes.NORMAL = accessor(mesh.normals, true, 34962)
    const primitives = [
      { attributes, indices: accessor(mesh.indices, false, 34963), mode: 4 },
    ]
    if (mesh.edgeIndices?.length) {
      primitives.push({
        attributes: { POSITION: position },
        indices: accessor(mesh.edgeIndices, false, 34963),
        mode: 1,
      })
    }
    triangles += mesh.indices.length / 3
    return { primitives, extras: { faces: mesh.faces } }
  })
  const nodes = meshes.map((_, mesh) => ({ mesh }))
  const gltf = {
    asset: { version: "2.0" },
    scene: 0,
    scenes: [{ nodes: nodes.map((_, i) => i) }],
    nodes,
    meshes: glMeshes,
    buffers: [{ byteLength: length }],
    bufferViews,
    accessors,
    extras: { coverRecipe: COVER_RECIPE, sourceHash, geometryKey },
  }
  const json = Buffer.from(JSON.stringify(gltf))
  const padded = Math.ceil(json.length / 4) * 4
  const size = 28 + padded + length
  if (size > 25 * 1024 * 1024)
    throw Error("Cover GLB exceeds the web size budget")
  const header = Buffer.alloc(20)
  header.write("glTF")
  header.writeUInt32LE(2, 4)
  header.writeUInt32LE(size, 8)
  header.writeUInt32LE(padded, 12)
  header.write("JSON", 16)
  const bin = Buffer.alloc(8)
  bin.writeUInt32LE(length)
  bin.write("BIN\0", 4)
  fs.writeFileSync(
    output,
    Buffer.concat(
      [header, json, Buffer.alloc(padded - json.length, 32), bin, ...chunks],
      size,
    ),
  )
  fs.writeFileSync(
    path.join(path.dirname(output), path.parse(output).name + ".json"),
    JSON.stringify({
      source_sha256: sourceHash,
      triangles,
      size,
      geometry_key: geometryKey,
    }),
  )
}
convert(process.argv[2], process.argv[3]).catch((error) => {
  console.error(error)
  process.exitCode = 1
})
