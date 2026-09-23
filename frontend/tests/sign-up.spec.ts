import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("Create account opens the placeholder", async ({ page }) => {
  await page.goto("/login")
  await page
    .getByRole("link", { name: "Crear una cuenta", exact: true })
    .click()
  await expect(page).toHaveURL("/signup")
  await expect(
    page.getByRole("heading", { name: "To be implemented", exact: true }),
  ).toBeVisible()
  await expect(page.getByTestId("password-input")).toHaveCount(0)
  await expect(page.getByRole("link")).toHaveCount(0)
})
