import type { Page } from "@playwright/test";
import { expect, test } from "@playwright/test";

const apiBaseUrl = "http://127.0.0.1:8100/";
const primaryMatchId = "00000000-0000-0000-0000-000000000101";
const sessionApiSummaryValue = (page: Page) =>
  page.locator(".session-summary div", { has: page.locator("dt", { hasText: "API" }) }).locator("dd");

test("walks the public demo path and shows auth-required guardrails without a saved token", async ({
  page
}) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Human Session Bootstrap" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Browser Session" })).toBeVisible();

  const apiBaseUrlInput = page.getByLabel("API base URL");
  await apiBaseUrlInput.fill(apiBaseUrl);
  await page.getByRole("button", { name: "Save session" }).click();
  await expect(page.getByText("Saved browser session for future authenticated flows.")).toBeVisible();
  await expect(sessionApiSummaryValue(page)).toHaveText("http://127.0.0.1:8100");

  await page.getByRole("link", { name: "View public matches" }).click();
  await expect(page).toHaveURL(/\/matches$/);
  await expect(page.getByRole("heading", { name: "Public Matches" })).toBeVisible();

  await page.getByRole("link", { name: `View details for ${primaryMatchId}` }).click();
  await expect(page).toHaveURL(new RegExp(`/matches/${primaryMatchId}$`));
  await expect(page.getByRole("heading", { name: `Public Match ${primaryMatchId}` })).toBeVisible();
  await expect(page.getByText("Arthur")).toBeVisible();
  await expect(page.getByText("Morgana")).toBeVisible();

  await page.goto(`/matches/${primaryMatchId}/history`);
  await expect(page.getByRole("heading", { name: "Match History" })).toBeVisible();
  await expect(page.getByText(`Match id: ${primaryMatchId}`)).toBeVisible();
  await expect(page.getByRole("link", { name: "Tick 142" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "State snapshot" })).toBeVisible();

  await page.goto(`/matches/${primaryMatchId}/live`);
  await expect(page.getByRole("heading", { name: `Live Match ${primaryMatchId}` })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Live spectator state" })).toBeVisible();
  await expect(page.getByText("Read-only spectator-safe state from the shipped match websocket contract.")).toBeVisible();

  await page.goto("/lobby");
  await expect(page.getByText("This route requires a configured human bearer token before later lobby and gameplay flows can open.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Return to public pages" })).toHaveAttribute("href", "/");

  await page.goto(`/matches/${primaryMatchId}/play`);
  await expect(page.getByRole("heading", { name: `Live Match ${primaryMatchId}` })).toBeVisible();
  await expect(page.getByText("This live player page requires a stored human bearer token before it can connect.")).toBeVisible();

  await page.reload();
  await expect(sessionApiSummaryValue(page)).toHaveText("http://127.0.0.1:8100");
  await expect(apiBaseUrlInput).toHaveValue("http://127.0.0.1:8100");
});
