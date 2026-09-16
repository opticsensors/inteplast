import { useEffect, useRef, useState } from "react"

// WebGL is exercised with the real STEP in the isolated browser check. This fixture
// isolates the form's draft, upload and save boundary from the CAD renderer.
export default function StepCoverCanvas({
  initial,
  onReady,
  onSelectionChange,
}) {
  const [count, setCount] = useState(initial?.faces.length ?? 0)
  const callbacks = useRef({ onReady, onSelectionChange })
  callbacks.current = { onReady, onSelectionChange }
  useEffect(() => {
    callbacks.current.onSelectionChange?.(count)
    callbacks.current.onReady?.({
      clear: () => setCount(0),
      capture: async () => ({
        image: new Blob(["test image"], { type: "image/png" }),
        annotation: {
          recipe: "occt-import-js@0.0.23/cover-v1",
          source_sha256: "a".repeat(64),
          geometry_key: "b".repeat(64),
          faces: [{ mesh: 0, face: 1 }],
          camera: { position: [10, -10, 10], target: [0, 0, 0], up: [0, 0, 1] },
        },
      }),
    })
    return () => callbacks.current.onReady?.(null)
  }, [count])
  return (
    <button type="button" onClick={() => setCount(count ? 0 : 1)}>
      Marcar superficie
    </button>
  )
}
