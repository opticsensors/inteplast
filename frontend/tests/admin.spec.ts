import { expect, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Admin page is accessible and shows correct title", async ({ page }) => {
  await page.goto("/admin")
  await expect(page.getByRole("heading", { name: "Usuarios" })).toBeVisible()
  await expect(
    page.getByText("Manage user accounts and permissions"),
  ).toHaveCount(0)
  await expect(
    page.getByRole("region", { name: "Datos de piezas" }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: "Reimportar archivos" }),
  ).toHaveCount(0)
})

test("Add User button is visible", async ({ page }) => {
  await page.goto("/admin")
  await expect(
    page.getByRole("button", { name: "Añadir usuario" }),
  ).toBeVisible()
})

test.describe("Admin user management", () => {
  test("Check a folder sample before saving the selection", async ({
    page,
  }) => {
    await page.route("**/api/v1/login/methods", (route) =>
      route.fulfill({
        json: { microsoft: true, password: false, sharepoint: true },
      }),
    )
    const current = {
      name: "Exemples",
      web_url: "https://demo.sharepoint.com/Exemples",
    }
    const candidate = {
      name: "Proyecto",
      web_url: "https://demo.sharepoint.com/Proyecto",
    }
    let active = current
    await page.route("**/api/v1/admin/originals", (route) => {
      if (route.request().method() === "PUT") {
        expect(route.request().postDataJSON()).toEqual({ ticket: "checked" })
        active = candidate
      }
      return route.fulfill({ json: active })
    })
    await page.route("**/api/v1/admin/originals/check", (route) =>
      route.fulfill({
        json: {
          folder: candidate,
          total: 21,
          checked: 3,
          found: 2,
          unavailable: ["Feature B/Pieza 2"],
          ticket: "checked",
        },
      }),
    )
    await page.goto("/admin")
    await expect(page.getByText("Exemples")).toHaveCount(0)
    await page.getByRole("button", { name: "SharePoint" }).click()
    const dialog = page.getByRole("dialog")
    await expect(
      dialog.getByRole("link", { name: "Abrir Exemples en SharePoint" }),
    ).toBeVisible()
    await dialog.getByLabel("Cambiar enlace carpeta:").fill(candidate.web_url)
    const save = dialog.getByRole("button", { name: "Guardar" })
    await expect(save).toBeDisabled()
    await dialog.getByRole("button", { name: "Comprobar" }).click()
    await expect(
      dialog.getByText(
        "Carpeta accesible · 2 de 3 carpetas de pieza encontradas",
      ),
    ).toBeVisible()
    await expect(dialog.getByText("Feature B/Pieza 2")).toBeVisible()
    expect(active).toEqual(current)
    await save.click()
    await expect(dialog).toHaveCount(0)
    expect(active).toEqual(candidate)
  })

  test("Add a Microsoft user with just their email", async ({ page }) => {
    await page.route("**/api/v1/login/methods", (route) =>
      route.fulfill({
        json: { microsoft: true, password: false, sharepoint: true },
      }),
    )
    const email = randomEmail()
    await page.route("**/api/v1/users/", async (route) => {
      if (route.request().method() !== "POST") return route.continue()
      expect(route.request().postDataJSON()).toEqual({ email })
      await route.fulfill({
        json: { email, is_active: true, is_superuser: false },
      })
    })
    await page.goto("/admin")
    await page.getByRole("button", { name: "Añadir usuario" }).click()
    const dialog = page.getByRole("dialog")
    await expect(dialog.locator("input")).toHaveCount(1)
    await expect(dialog.getByRole("checkbox")).toHaveCount(0)
    await dialog.getByLabel("Correo").fill(email)
    await dialog.getByRole("button", { name: "Guardar" }).click()
    await expect(page.getByText("Usuario creado")).toBeVisible()
  })

  test("Create a new user successfully", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()
    const fullName = "Test User Admin"

    await page.getByRole("button", { name: "Añadir usuario" }).click()

    await page.getByPlaceholder("Correo").fill(email)
    await page.getByPlaceholder("Nombre").fill(fullName)
    await page.getByPlaceholder("Contraseña").first().fill(password)
    await page.getByPlaceholder("Contraseña").last().fill(password)

    await page.getByRole("button", { name: "Guardar" }).click()

    await expect(page.getByText("Usuario creado")).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await expect(userRow).toBeVisible()
  })

  test("Create a superuser", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()

    await page.getByRole("button", { name: "Añadir usuario" }).click()

    await page.getByPlaceholder("Correo").fill(email)
    await page.getByPlaceholder("Contraseña").first().fill(password)
    await page.getByPlaceholder("Contraseña").last().fill(password)
    await page.getByLabel("Admin").check()
    await page.getByLabel("Cuenta activa").check()

    await page.getByRole("button", { name: "Guardar" }).click()

    await expect(page.getByText("Usuario creado")).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await expect(userRow.getByText("Admin")).toBeVisible()
  })

  test("Edit only a user's role and status", async ({ page }) => {
    const email = randomEmail()
    const user = await createUser({ email, password: randomPassword() })
    await page.goto("/admin")
    const userRow = page.getByRole("row").filter({ hasText: email })
    await userRow.getByRole("button").click()
    await page.getByRole("menuitem", { name: "Editar usuario" }).click()
    const dialog = page.getByRole("dialog", { name: "Editar usuario" })
    await expect(dialog.getByText(email, { exact: true })).toBeVisible()
    await expect(dialog.locator("input")).toHaveCount(0)
    const role = dialog.getByRole("combobox", { name: "Rol" })
    const status = dialog.getByRole("combobox", { name: "Estado" })
    await expect(role).toHaveText("Usuario")
    await expect(status).toHaveText("Activo")
    await role.click()
    await page.getByRole("option", { name: "Admin" }).click()
    await status.click()
    await page.getByRole("option", { name: "Inactivo" }).click()
    const update = page.waitForRequest(
      (req) =>
        req.method() === "PATCH" && req.url().endsWith(`/users/${user.id}`),
    )
    await dialog.getByRole("button", { name: "Guardar" }).click()
    expect((await update).postDataJSON()).toEqual({
      is_superuser: true,
      is_active: false,
    })
    await expect(page.getByText("Usuario actualizado")).toBeVisible()
    await expect(userRow.getByText("Admin", { exact: true })).toBeVisible()
    await expect(userRow.getByText("Inactivo", { exact: true })).toBeVisible()
  })

  test("Delete a user successfully", async ({ page }) => {
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()

    await page.getByRole("button", { name: "Añadir usuario" }).click()
    await page.getByPlaceholder("Correo").fill(email)
    await page.getByPlaceholder("Contraseña").first().fill(password)
    await page.getByPlaceholder("Contraseña").last().fill(password)
    await page.getByRole("button", { name: "Guardar" }).click()

    await expect(page.getByText("Usuario creado")).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await userRow.getByRole("button").click()

    await page.getByRole("menuitem", { name: "Eliminar usuario" }).click()

    await page.getByRole("button", { name: "Eliminar" }).click()

    await expect(page.getByText("Usuario eliminado")).toBeVisible()

    await expect(
      page.getByRole("row").filter({ hasText: email }),
    ).not.toBeVisible()
  })

  test("Cancel user creation", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "Añadir usuario" }).click()
    await page.getByPlaceholder("Correo").fill("test@example.com")

    await page.getByRole("button", { name: "Cancelar" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
  })

  test("Email is validated only on Save without visible messages", async ({
    page,
  }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "Añadir usuario" }).click()

    await page.getByPlaceholder("Correo").fill("invalid-email")
    await page.getByPlaceholder("Correo").blur()

    await expect(page.getByPlaceholder("Correo")).toHaveAttribute(
      "aria-invalid",
      "false",
    )
    await page.getByRole("button", { name: "Guardar" }).click()
    await expect(page.getByPlaceholder("Correo")).toHaveAttribute(
      "aria-invalid",
      "true",
    )
    await expect(
      page.locator('[data-slot="form-message"]:not(.sr-only)'),
    ).toHaveCount(0)
  })

  test("La contraseña debe tener al menos 8 caracteres", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "Añadir usuario" }).click()

    await page.getByPlaceholder("Correo").fill(randomEmail())
    await page.getByPlaceholder("Contraseña").first().fill("short")
    await page.getByPlaceholder("Contraseña").last().fill("short")
    await page.getByRole("button", { name: "Guardar" }).click()

    await expect(page.getByPlaceholder("Contraseña").first()).toHaveAttribute(
      "aria-invalid",
      "true",
    )
    await expect(
      page.locator('[data-slot="form-message"]:not(.sr-only)'),
    ).toHaveCount(0)
  })

  test("Passwords must match", async ({ page }) => {
    await page.goto("/admin")

    await page.getByRole("button", { name: "Añadir usuario" }).click()

    await page.getByPlaceholder("Correo").fill(randomEmail())
    await page.getByPlaceholder("Contraseña").first().fill(randomPassword())
    await page.getByPlaceholder("Contraseña").last().fill("different12345")
    await page.getByPlaceholder("Contraseña").last().blur()

    await expect(page.getByPlaceholder("Contraseña").last()).toHaveAttribute(
      "aria-invalid",
      "false",
    )
    await page.getByRole("button", { name: "Guardar" }).click()
    await expect(page.getByPlaceholder("Contraseña").last()).toHaveAttribute(
      "aria-invalid",
      "true",
    )
    await expect(
      page.locator('[data-slot="form-message"]:not(.sr-only)'),
    ).toHaveCount(0)
  })
})

test.describe("Admin page access control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Non-superuser cannot access admin page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()

    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/admin")

    await expect(
      page.getByRole("heading", { name: "Usuarios" }),
    ).not.toBeVisible()
    await expect(page).not.toHaveURL(/\/admin/)
  })

  test("Superuser can access admin page", async ({ page }) => {
    await logInUser(page, firstSuperuser, firstSuperuserPassword)

    await page.goto("/admin")

    await expect(page.getByRole("heading", { name: "Usuarios" })).toBeVisible()
  })
})
