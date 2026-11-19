import { createContext } from "react"

/**
 * Called once the server confirms that this page unlinked a piece from the feature.
 * The feature editor drops that piece's unsaved cover; a failed unlink keeps it.
 */
export const PartUnlinkedContext = createContext<(partId: string) => void>(
  () => {},
)
