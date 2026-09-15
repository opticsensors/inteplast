import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRoot } from "react-dom/client"
import {
  fileAction,
  usesWebPreview,
} from "../../../src/components/Features/viewers"
import WebModelViewer from "../../../src/components/Features/WebModelViewer"

const root = createRoot(document.getElementById("root"))
const file = { id: "large-scan", filename: "scan.stl", size: 247145084 }
window.preview = {
  calls: [],
  states: [
    { state: "queued" },
    { state: "processing" },
    { state: "ready", url: "/small.glb" },
  ],
  action: (filename, size) => fileAction({ ...file, filename, size }),
  usesPreview: (filename, size) => usesWebPreview({ ...file, filename, size }),
  mount: () =>
    root.render(
      <QueryClientProvider client={new QueryClient()}>
        <WebModelViewer file={file} />
      </QueryClientProvider>,
    ),
  unmount: () => root.render(null),
}
window.preview.mount()
