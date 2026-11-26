import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

test("CAD preferences persist across sessions and reset independently of covers", async ({
  page,
  browser,
}) => {
  const email = randomEmail()
  const password = randomPassword()
  await createUser({ email, password })
  await logInUser(page, email, password)
  await page.goto("/settings")
  const coverWrites: string[] = []
  page.on("request", (request) => {
    if (
      request.method() !== "GET" &&
      /\/(features|parts|files)(\/|\?|$)/.test(new URL(request.url()).pathname)
    )
      coverWrites.push(request.url())
  })
  const radio = (name: string) => page.getByRole("radio", { name, exact: true })
  await expect(radio("Ortográfica")).toBeChecked()
  await expect(radio("Trackball")).toBeChecked()
  const zoom = "Invertir zoom con la ruedilla"
  const pickCenter = "Elegir el centro de giro con un clic de la ruedilla"
  await expect(page.getByRole("checkbox", { name: pickCenter })).toBeChecked()
  await expect(page.getByRole("checkbox", { name: zoom })).toBeChecked()
  const choices = ["Perspectiva 45°", "Clásico"]
  for (const name of choices) {
    const saved = page.waitForResponse(
      (response) =>
        response.url().endsWith("/users/me/cad-preferences") &&
        response.status() === 200,
    )
    await page.getByText(name, { exact: true }).click()
    await saved
    await expect(radio(name)).toBeChecked()
  }
  for (const name of [pickCenter, zoom]) {
    const checkbox = page.getByRole("checkbox", { name })
    await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().endsWith("/users/me/cad-preferences") && response.ok(),
      ),
      checkbox.click(),
    ])
    await expect(checkbox).not.toBeChecked()
  }
  const second = await browser.newPage({ baseURL: new URL(page.url()).origin })
  try {
    await logInUser(second, email, password)
    await second.goto("/settings")
    await expect(
      second.getByRole("checkbox", { name: pickCenter }),
    ).not.toBeChecked()
    await expect(second.getByRole("checkbox", { name: zoom })).not.toBeChecked()
    for (const name of choices) {
      await expect(
        second.getByRole("radio", { name, exact: true }),
      ).toBeChecked()
    }
  } finally {
    await second.close()
  }
  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith("/users/me/cad-preferences") &&
      response.status() === 200,
  )
  await page.getByRole("button", { name: "Restablecer" }).click()
  await saved
  await page.reload()
  await expect(radio("Trackball")).toBeChecked()
  await expect(page.getByRole("checkbox", { name: pickCenter })).toBeChecked()
  await expect(radio("Ortográfica")).toBeChecked()
  await expect(page.getByRole("checkbox", { name: zoom })).toBeChecked()
  expect(coverWrites).toEqual([])
})
