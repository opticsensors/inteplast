import { expect, type Page, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { randomPassword } from "./utils/random.ts"

test.use({ storageState: { cookies: [], origins: [] } })

const fillForm = async (page: Page, email: string, password: string) => {
  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
}

const verifyInput = async (page: Page, testId: string) => {
  const input = page.getByTestId(testId)
  await expect(input).toBeVisible()
  await expect(input).toHaveText("")
  await expect(input).toBeEditable()
}

test("Empty inputs are editable and only become invalid on submit", async ({
  page,
}) => {
  await page.goto("/login")

  await verifyInput(page, "email-input")
  await verifyInput(page, "password-input")
  for (const testId of ["email-input", "password-input"]) {
    const input = page.getByTestId(testId)
    await input.focus()
    await input.blur()
    await expect(input).toHaveAttribute("aria-invalid", "false")
  }
  await page.getByRole("button", { name: "Iniciar sesión" }).click()
  for (const testId of ["email-input", "password-input"]) {
    await expect(page.getByTestId(testId)).toHaveAttribute(
      "aria-invalid",
      "true",
    )
  }
  await expect(
    page.locator('[data-slot="form-message"]:not(.sr-only)'),
  ).toHaveCount(0)
})

test("Log In button is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(
    page.getByRole("button", { name: "Iniciar sesión" }),
  ).toBeVisible()
})

test("Forgot Password link is visible", async ({ page }) => {
  await page.goto("/login")

  await expect(
    page.getByRole("link", { name: "¿Olvidaste tu contraseña?" }),
  ).toBeVisible()
})

test("Log in with valid email and password ", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "Iniciar sesión" }).click()

  await page.waitForURL("/features")

  await expect(
    page.getByRole("heading", { name: "Features", exact: true }),
  ).toBeVisible()
})

test("Log in with invalid email", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, "invalidemail", firstSuperuserPassword)
  await page.getByTestId("password-input").blur()
  await expect(page.getByTestId("email-input")).toHaveAttribute(
    "aria-invalid",
    "false",
  )
  await page.getByRole("button", { name: "Iniciar sesión" }).click()

  await expect(page.getByTestId("email-input")).toHaveAttribute(
    "aria-invalid",
    "true",
  )
  await expect(
    page.locator('[data-slot="form-message"]:not(.sr-only)'),
  ).toHaveCount(0)
})

test("Log in with invalid password", async ({ page }) => {
  const password = randomPassword()

  await page.goto("/login")
  await fillForm(page, firstSuperuser, password)
  await page.getByRole("button", { name: "Iniciar sesión" }).click()

  await expect(page.getByText("Incorrect email or password")).toBeVisible()
})

test("Successful log out", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "Iniciar sesión" }).click()

  await page.waitForURL("/features")

  await expect(
    page.getByRole("heading", { name: "Features", exact: true }),
  ).toBeVisible()

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL("/login")
})

test("Logged-out user cannot access protected routes", async ({ page }) => {
  await page.goto("/login")

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole("button", { name: "Iniciar sesión" }).click()

  await page.waitForURL("/features")

  await expect(
    page.getByRole("heading", { name: "Features", exact: true }),
  ).toBeVisible()

  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log out" }).click()
  await page.waitForURL("/login")

  await page.goto("/settings")
  await page.waitForURL("/login")
})

test("Redirects to /login when token is wrong", async ({ page }) => {
  await page.goto("/settings")
  await page.evaluate(() => {
    localStorage.setItem("access_token", "invalid_token")
  })
  await page.goto("/settings")
  await page.waitForURL("/login")
  await expect(page).toHaveURL("/login")
})
