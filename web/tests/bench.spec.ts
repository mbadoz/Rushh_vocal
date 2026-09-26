import { test, expect } from "@playwright/test";
test("composer, persistence, keys and empty states", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("Mot de passe").fill("test-password");
  await page.getByRole("button", { name: /Ouvrir le laboratoire/ }).click();
  await expect(
    page.getByRole("heading", { name: "Composez votre agent." }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Comprendre" })).toBeVisible();
  await page.getByText("Paramètres du modèle", { exact: true }).first().click();
  const sttCard = page.locator(".model-card").first();
  const added = sttCard.getByLabel("sample rate", { exact: true });
  if (!(await added.count())) {
    await page
      .getByLabel("Ajouter un réglage du plugin")
      .first()
      .selectOption("sample_rate");
  }
  await expect(added).toBeVisible();
  await added.fill("16000");
  await page.getByText("Paramètres du modèle", { exact: true }).first().click();
  await page
    .getByLabel("Nom", { exact: true })
    .fill("Composition test navigateur");
  await page.getByRole("button", { name: "Enregistrer", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Composition enregistrée",
  );
  await page.reload();
  await expect(page.getByLabel("Nom", { exact: true })).toHaveValue(
    "Composition test navigateur",
  );
  await page.screenshot({ path: "/tmp/rushh-composer.png", fullPage: true });
  await page
    .getByRole("button", { name: "Speech-to-speech", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Converser", exact: true }),
  ).toBeVisible();
  for (const tab of [
    "Tester",
    "Historique",
    "Comparatif",
    "Prix",
    "Clés API",
  ]) {
    await page.getByRole("button", { name: tab, exact: true }).click();
    await expect(page.locator("h1")).toBeVisible();
  }
  const card = page.locator(".key-card").filter({
    has: page.getByRole("heading", { name: "soniox", exact: true }),
  });
  await card.getByLabel("Ajouter une clé").fill("local-browser-test-1234");
  await card.getByRole("button", { name: "Enregistrer", exact: true }).click();
  await expect(card).toContainText("••••1234");
  await expect(card.locator("input[type=password]")).toHaveValue("");
  await card.getByRole("button", { name: "Supprimer", exact: true }).click();
  await expect(card).toContainText("Aucune clé enregistrée");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Composer", exact: true }).click();
  await page.screenshot({ path: "/tmp/rushh-mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
