import { expect, test } from "@playwright/test";

test("loads the mobile login and public health endpoint", async ({ page, request }) => {
  const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";
  const health = await request.get(`${apiURL}/api/v1/health`);
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toEqual(
    expect.objectContaining({ status: "ok", service: "hospitaPulse-api" }),
  );

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Inicia sesión" })).toBeVisible();
  await expect(page.getByLabel("Usuario")).toBeVisible();
  await expect(page.getByLabel("Contraseña")).toBeVisible();
  await expect(page.getByRole("button", { name: "Ingresar" })).toBeVisible();
});

test("administrator signs in and views protected indicators", async ({ page }) => {
  const username = process.env.E2E_ADMIN_USERNAME;
  const password = process.env.E2E_ADMIN_PASSWORD;
  test.skip(!username || !password, "E2E_ADMIN_USERNAME/E2E_ADMIN_PASSWORD no configuradas");

  await page.goto("/");
  await page.getByLabel("Usuario").fill(username!);
  await page.getByLabel("Contraseña").fill(password!);
  await page.getByRole("button", { name: "Ingresar" }).click();

  await expect(page.getByRole("heading", { name: "El pulso de nuestra comunidad" })).toBeVisible();
  await expect(page.getByText("RESPUESTAS RECIBIDAS", { exact: true })).toBeVisible();
  await expect(page.getByText(
    /Muestra protegida|Protección de privacidad|Datos del periodo seleccionado/,
  ).first()).toBeVisible();
});

test("staff completes the monthly survey after changing the temporary password", async ({ page }) => {
  const adminUsername = process.env.E2E_ADMIN_USERNAME;
  const adminPassword = process.env.E2E_ADMIN_PASSWORD;
  test.skip(!adminUsername || !adminPassword, "E2E_ADMIN_USERNAME/E2E_ADMIN_PASSWORD no configuradas");

  const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";
  const suffix = Date.now();
  const username = `e2e-${suffix}`;

  await page.goto("/");
  await page.getByLabel("Usuario").fill(adminUsername!);
  await page.getByLabel("Contraseña").fill(adminPassword!);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { name: "El pulso de nuestra comunidad" })).toBeVisible();

  const createUser = await page.context().request.post(`${apiURL}/api/v1/personal`, {
    data: {
      username,
      nombre_completo: "Usuario de prueba E2E",
      email: `${username}@example.com`,
      rol: "staff",
    },
  });
  expect(createUser.status()).toBe(201);
  const createdUser = await createUser.json() as { password_temporal: string };

  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await page.goto("/encuestas");
  await page.getByLabel("Usuario").fill(username);
  await page.getByLabel("Contraseña").fill(createdUser.password_temporal);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();

  await expect(page.getByRole("heading", { name: "Cambia tu contraseña temporal" })).toBeVisible();
  const newPassword = `E2E-Change-${suffix}!`;
  await page.getByLabel("Contraseña temporal").fill(createdUser.password_temporal);
  await page.getByLabel("Nueva contraseña").fill(newPassword);
  await page.getByRole("button", { name: "Cambiar contraseña y continuar" }).click();

  const questions = page.locator("fieldset.survey-question");
  await expect(questions).toHaveCount(5);
  for (let index = 0; index < 5; index += 1) {
    await questions.nth(index).getByRole("radio").last().check();
  }
  await page.getByRole("button", { name: /Enviar respuesta anónima/ }).click();
  await expect(page.getByRole("heading", { name: "¡Gracias por participar!" })).toBeVisible();
});
