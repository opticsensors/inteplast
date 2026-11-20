type Face = { first: number; last: number }

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
