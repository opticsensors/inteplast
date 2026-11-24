type Face = { first: number; last: number }

/** On a single CAD face an interior triangulation segment occurs twice. Only
 * the perimeter remains, including tangent joins between neighbouring faces. */
export function cadBoundaryIndices(
  index: ArrayLike<number> | undefined,
  stride: number,
  faces: Face[],
) {
  if (!index || !faces.length) return undefined
  const segments: number[] = []
  for (const { first, last } of faces) {
    const boundary = new Set<number>()
    for (let triangle = first; triangle <= last; triangle++) {
      const start = triangle * 3
      let a = index[start + 2]
      for (let corner = 0; corner < 3; corner++) {
        const b = index[start + corner]
        if (a !== b) {
          const key = Math.min(a, b) * stride + Math.max(a, b)
          if (!boundary.delete(key)) boundary.add(key)
        }
        a = b
      }
    }
    for (const key of boundary)
      segments.push(Math.floor(key / stride), key % stride)
  }
  return Uint32Array.from(segments)
}

/** OCCT keeps a face index even when tessellation emitted no triangles for it. */
export function coverFaceRanges(faces: Face[], triangles: number) {
  const ranges: (Face & { faceIndex: number })[] = []
  let next = 0
  faces.forEach(({ first, last }, faceIndex) => {
    if (first === next && last === first - 1) return
    if (
      !Number.isInteger(first) ||
      !Number.isInteger(last) ||
      first < next ||
      last < first ||
      last >= triangles
    )
      throw new Error("El STEP no conserva superficies seleccionables válidas.")
    ranges.push({ first, last, faceIndex })
    next = last + 1
  })
  return ranges
}
