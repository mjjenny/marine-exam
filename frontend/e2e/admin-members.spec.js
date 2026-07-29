import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

/**
 * Locators mirrored from AdminUsers.jsx:
 *   <h1>Members</h1>
 *   <input type="search" aria-label="Search by email" placeholder="Search by email..." />
 *   <button>Revoke</button>
 *   <h2>Revoke access?</h2>
 *   <button>Cancel</button>
 */
test.describe("Admin Members dashboard", () => {
  test("admin can open Members, search, and see Revoke controls", async ({ page }) => {
    await loginAs(page, USERS.admin);
    await page.goto("/admin/users");

    // Exact match to <h1>Members</h1> in AdminUsers.jsx
    await expect(page.getByRole("heading", { level: 1, name: "Members" })).toBeVisible();

    // Seeded searchable member appears in the table.
    await expect(page.getByText(USERS.searchable.email)).toBeVisible();

    // Matches aria-label="Search by email" on the search input.
    const search = page.getByLabel("Search by email");
    await search.fill("searchable@e2e");
    await expect(page.getByText(USERS.searchable.email)).toBeVisible();
    await expect(page.getByText(USERS.member.email)).toHaveCount(0);

    // Row action button text is exactly "Revoke".
    const row = page.locator("tr", { hasText: USERS.searchable.email });
    await expect(row.getByRole("button", { name: "Revoke", exact: true })).toBeVisible();

    // Modal heading is exactly "Revoke access?" (h2 in RevokeModal).
    await row.getByRole("button", { name: "Revoke", exact: true }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Revoke access?" })).toBeVisible();
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Revoke access?" })).toHaveCount(0);
  });
});
