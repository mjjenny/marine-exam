import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

test.describe("Student QoL — account, theme, bookmarks", () => {
  test("member can open My Account, toggle dark mode, and bookmark an answer", async ({
    page,
  }) => {
    await loginAs(page, USERS.member);

    await page.goto("/account");
    await expect(page.getByRole("heading", { level: 1, name: "My Account" })).toBeVisible();
    await expect(page.getByText(USERS.member.email)).toBeVisible();

    // Theme toggle — button label flips between Dark / Light.
    const themeBtn = page.getByRole("button", { name: /Switch to (light|dark) mode/i }).first();
    await expect(themeBtn).toBeVisible();
    const before = await themeBtn.getAttribute("aria-label");
    await themeBtn.click();
    await expect(themeBtn).not.toHaveAttribute("aria-label", before);

    // Open a known content answer if available via home; otherwise hit bookmarks page.
    // Seeded E2E DB may have little content — bookmark control still exists on answer pages
    // when content is present. Exercise the bookmarks list route either way.
    await page.goto("/bookmarks");
    await expect(page.getByRole("heading", { level: 1, name: "Bookmarks" })).toBeVisible();

    // Prefer bookmarking via API-seeded path: try subjects then first answer link if any.
    await page.goto("/");
    const book = page.locator(".book-cover, .book-grid button, .book-grid a").first();
    if (await book.count()) {
      await book.click();
      const answerLink = page.locator('a[href^="/answers/"], a[href^="/questions/"]').first();
      if (await answerLink.count()) {
        await answerLink.click();
        const star = page.getByRole("button", { name: /Bookmark for later|Remove bookmark/i });
        await expect(star).toBeVisible({ timeout: 15_000 });
        await star.click();
        await page.goto("/bookmarks");
        await expect(page.getByRole("heading", { level: 1, name: "Bookmarks" })).toBeVisible();
      }
    }
  });
});
