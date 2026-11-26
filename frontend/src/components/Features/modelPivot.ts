import { Box3, Mesh, type Object3D, Vector3 } from "three"

/** Integrate signed tetrahedra for a closed, consistently wound triangle mesh.
 * CAD tessellation duplicates vertices at face seams, so compare positions
 * across all meshes before checking that every edge has an opposite partner. */
export function modelPivot(object: Object3D) {
  const bounds = new Box3().setFromObject(object)
  const center = bounds.getCenter(new Vector3())
  const size = bounds.getSize(new Vector3()).length()
  const meshes: Mesh[] = []
  object.traverseVisible((node) => {
    if (node instanceof Mesh && node.geometry.getAttribute("position"))
      meshes.push(node)
  })
  if (!meshes.length || !size) return center
  const stride = meshes.reduce(
    (count, mesh) => count + mesh.geometry.getAttribute("position").count,
    0,
  )
  const tolerance = size * 1e-7
  const vertexIds = new Map<string, number>()
  const points: Vector3[] = []
  const edges = new Map<number, number>()
  const point = new Vector3(),
    cross = new Vector3(),
    moment = new Vector3()
  let volume6 = 0
  function pairEdge(a: number, b: number) {
    const key = Math.min(a, b) * stride + Math.max(a, b)
    const direction = a < b ? 1 : -1
    const other = edges.get(key)
    if (other !== undefined && other !== -direction) return false
    edges.set(key, other === undefined ? direction : 0)
    return true
  }
  for (const mesh of meshes) {
    const positions = mesh.geometry.getAttribute("position")
    const ids = new Uint32Array(positions.count)
    for (let i = 0; i < positions.count; i++) {
      point
        .fromBufferAttribute(positions, i)
        .applyMatrix4(mesh.matrixWorld)
        .sub(center)
      const key = `${Math.round(point.x / tolerance)},${Math.round(point.y / tolerance)},${Math.round(point.z / tolerance)}`
      let id = vertexIds.get(key)
      if (id === undefined) {
        id = points.length
        vertexIds.set(key, id)
        points.push(point.clone())
      }
      ids[i] = id
    }
    const index = mesh.geometry.index
    const count = index?.count ?? positions.count
    for (let i = 0; i + 2 < count; i += 3) {
      const a = ids[index ? index.getX(i) : i]
      const b = ids[index ? index.getX(i + 1) : i + 1]
      const c = ids[index ? index.getX(i + 2) : i + 2]
      if (a === b || b === c || a === c) continue
      if (!pairEdge(a, b) || !pairEdge(b, c) || !pairEdge(c, a)) return center
      const v = points[a].dot(cross.crossVectors(points[b], points[c]))
      volume6 += v
      moment
        .addScaledVector(points[a], v)
        .addScaledVector(points[b], v)
        .addScaledVector(points[c], v)
    }
  }
  for (const balance of edges.values()) if (balance !== 0) return center
  if (Math.abs(volume6) <= Number.EPSILON * size ** 3) return center
  const centroid = moment.multiplyScalar(1 / (4 * volume6)).add(center)
  return bounds.containsPoint(centroid) ? centroid : center
}
