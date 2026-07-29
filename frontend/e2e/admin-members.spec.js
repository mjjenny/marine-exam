import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

test.describe("Admin Members dashboard", () => {
  test("admin can open Members, search, and see Revoke controls", async ({ page }) => {
    await loginAs(page, USERS.admin);
    await page.goto("/admin/users");

    await expect(page.getByRole("heading", { name: "Members", exact: true })).toBeVisible();

    // Seeded searchable member appears in the table.
    await expect(page.getByText(USERS.searchable.email)).toBeVisible();

    const search = page.getByRole("searchbox", { name: /Search by email/i });
    await search.fill("searchable@e2e");
    await expect(page.getByText(USERS.searchable.email)).toBeVisible();
    await expect(page.getByText(USERS.member.email)).toHaveCount(0);

    // Revoke button present for non-admin, non-revoked members.
    const row = page.locator("tr", { hasText: USERS.searchable.email });
    await expect(row.getByRole("button", { name: /Revoke/i })).toBeVisible();

    // Open confirmation modal then cancel (no destructive side-effect in CI).
    await row.getByRole("button", { name: /Revoke/i }).click();
    await expect(page.getByRole("heading", { name: /Revoke access/i })).toBeVisible();
    await page.getByRole("button", { name: /Cancel/i }).click();
    await expect(page.getByRole("heading", { name: /Revoke access/i })).toHaveCount(0);
  });
});
