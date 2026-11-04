// Load a fixture page once before the tests of a file run.
//
// A fresh Vite dev server compiles the fixture's module graph on the first request.
// Measured on 04/11/2026: ~20 s of the first test in each Vite-based file was that
// compilation, and with the four servers starting at the same time it exceeded the
// tests' navigation timeouts. Doing it here keeps that one-off cost out of the tests,
// whose own timeouts stay unchanged. Production serves a prebuilt bundle.
const WARM_UP_TIMEOUT_MS = 180_000

async function warmUp(browser, url) {
  const origin = new URL(url).origin
  const page = await browser.newPage()
  try {
    await page.route("**/*", (route) =>
      route.request().url().startsWith(origin)
        ? route.continue()
        : route.abort(),
    )
    await page.goto(url, { waitUntil: "load", timeout: WARM_UP_TIMEOUT_MS })
  } finally {
    await page.close()
  }
}

module.exports = { warmUp }
