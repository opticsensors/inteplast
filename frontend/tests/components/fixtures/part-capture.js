export async function capturePartCad(_file, signal) {
  signal.throwIfAborted()
  window.review.captures += 1
  return {
    image: new Blob(["test"], { type: "image/png" }),
    sourceHash: "a".repeat(64),
  }
}
