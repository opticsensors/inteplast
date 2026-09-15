import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("Account requests go through the administrator", async ({ page }) => {
  await page.goto("/signup")
  await expect(
    page.getByRole("heading", { name: "Solicitar acceso" }),
  ).toBeVisible()
  await expect(
    page.getByText("Contacta con el administrador para solicitar una cuenta."),
  ).toBeVisible()
  await expect(page.getByTestId("password-input")).toHaveCount(0)
  await page.getByRole("link", { name: "Volver al inicio de sesion" }).click()
  await expect(page).toHaveURL("/login")
  await expect(
    page.getByRole("link", { name: "Sign up", exact: true }),
  ).toHaveCount(0)
})
