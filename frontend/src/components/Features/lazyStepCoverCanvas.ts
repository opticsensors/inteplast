import { lazy } from "react"

const loadViewer = () => import("@/components/Features/StepCoverCanvas")
export const StepCoverCanvas = lazy(loadViewer)

// Start downloading the viewer code on intent. The STEP is read on opening.
export function preloadStepViewer() {
  void loadViewer().catch(() => {})
}
