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
  await expect(radio("Tipo SolidWorks")).toBeChecked()
  await expect(radio("Hacia la pantalla")).toBeChecked()
  for (const name of ["Perspectiva 45°", "Clásicos", "Hacia ti"]) {
    const saved = page.waitForResponse(
      (response) =>
        response.url().endsWith("/users/me/cad-preferences") &&
        response.status() === 200,
    )
    await page.getByText(name, { exact: true }).click()
    await saved
    await expect(radio(name)).toBeChecked()
  }
  const second = await browser.newPage({ baseURL: new URL(page.url()).origin })
  try {
    await logInUser(second, email, password)
    await second.goto("/settings")
    for (const name of ["Perspectiva 45°", "Clásicos", "Hacia ti"]) {
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
  await page
    .getByRole("button", { name: "Restablecer valores predeterminados" })
    .click()
  await saved
  await page.reload()
  await expect(radio("Ortográfica")).toBeChecked()
  await expect(radio("Tipo SolidWorks")).toBeChecked()
  await expect(radio("Hacia la pantalla")).toBeChecked()
  expect(coverWrites).toEqual([])
})
