import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

test.describe("Auth flow", () => {
  test("successful login reaches the home page", async ({ page }) => {
    await loginAs(page, USERS.member);
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    // Greeting uses the email local-part ("Member" from member@e2e.local).
    await expect(page.getByText(/Good (morning|afternoon|evening)/i)).toBeVisible({
      timeout: 15_000,
    });
    // Static bookshelf with clickable subject books (BookCover aria-label / data-testid).
    await expect(page.getByTestId("bookshelf")).toBeVisible();
    await expect(page.getByRole("button", { name: /^Open / }).first()).toBeVisible();
  });

  test("invalid credentials show an error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(USERS.member.email);
    await page.getByLabel("Password").fill("WrongPass1!");
    await page.getByRole("button", { name: /^Log in$/i }).click();
    await expect(page.locator(".form-error")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("revoked user is blocked from the app", async ({ page }) => {
    await loginAs(page, USERS.revoked);
    await expect(page).toHaveURL(/\/pending/);
    await expect(page.getByRole("heading", { name: /Access revoked/i })).toBeVisible();
  });
});
