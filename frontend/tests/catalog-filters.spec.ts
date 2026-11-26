import { expect, test } from "@playwright/test"

test("the five catalogue filters share one desktop row and fit a phone", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto("/features")
  await page.getByRole("button", { name: "Filtros", exact: true }).click()
  const filters = ["Pieza", "Feature", "Familia", "Cliente", "Material"].map(
    (name) => page.getByRole("combobox", { name, exact: true }),
  )
  const desktop = []
  for (const filter of filters) {
    await expect(filter).toBeVisible()
    desktop.push((await filter.boundingBox())!)
  }
  for (const box of desktop)
    expect(Math.abs(box.y - desktop[0].y)).toBeLessThan(2)
  await page.setViewportSize({ width: 390, height: 844 })
  for (const filter of filters) {
    const box = (await filter.boundingBox())!
    expect(box.x).toBeGreaterThanOrEqual(0)
    expect(box.x + box.width).toBeLessThanOrEqual(390)
  }
})
