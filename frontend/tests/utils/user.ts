import { expect, type Page } from "@playwright/test"
import { createUser } from "./privateApi"

export async function signUpNewUser(
  page: Page,
  _name: string,
  email: string,
  password: string,
) {
  await createUser({ email, password })
  await page.goto("/login")
}

export async function logInUser(page: Page, email: string, password: string) {
  await page.goto("/login")

  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
  await page.getByRole("button", { name: "Iniciar sesión" }).click()
  await page.waitForURL("/features")
  await expect(
    page.getByRole("heading", { name: "Features", exact: true }),
  ).toBeVisible()
}

export async function logOutUser(page: Page) {
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.goto("/login")
}
