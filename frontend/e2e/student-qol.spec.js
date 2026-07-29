import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

/**
 * Locators mirrored from:
 *   MyAccount.jsx      — h1 "My Account", aria-label="Account email"
 *   ThemeToggle.jsx    — data-testid="theme-toggle", aria-label Switch to light/dark mode
 *   BookmarkButton.jsx — data-testid="bookmark-button", aria-label Bookmark for later / Remove bookmark
 *   Bookmarks.jsx      — h1 "Bookmarks", list shows "Answer #<id>"
 *
 * Content: `flask seed-e2e` creates subject slug `e2e-motor` + answer titled "E2E sample answer".
 */
test.describe("Student QoL — account, theme, bookmarks", () => {
  test("member can open My Account, toggle theme, and click bookmark", async ({ page }) => {
    await loginAs(page, USERS.member);

    // --- My Account ---
    await page.goto("/account");
    await expect(page.getByRole("heading", { level: 1, name: "My Account" })).toBeVisible();
    // aria-label avoids strict-mode clash with the desktop header email text.
    await expect(page.getByLabel("Account email")).toHaveText(USERS.member.email);

    // --- Theme (exactly one ThemeToggle is CSS-visible per viewport) ---
    const themeBtn = page.locator('[data-testid="theme-toggle"]:visible');
    await expect(themeBtn).toHaveCount(1);
    const labelBefore = await themeBtn.getAttribute("aria-label");
    expect(
      labelBefore === "Switch to light mode" || labelBefore === "Switch to dark mode"
    ).toBeTruthy();
    await themeBtn.click();
    await expect(themeBtn).not.toHaveAttribute("aria-label", labelBefore);

    // --- Bookmarks page heading ---
    await page.goto("/bookmarks");
    await expect(page.getByRole("heading", { level: 1, name: "Bookmarks" })).toBeVisible();

    // --- Open seeded E2E answer and click the star ---
    const answerId = await page.evaluate(async () => {
      const subjects = await fetch("/api/subjects", { credentials: "same-origin" }).then((r) =>
        r.json()
      );
      const e2e = (subjects || []).find((s) => s.slug === "e2e-motor");
      if (!e2e) return null;
      const idx = await fetch(`/api/subjects/${e2e.slug}/index`, {
        credentials: "same-origin",
      }).then((r) => r.json());
      const entry = (idx.entries || []).find((e) => e.question === "E2E sample answer");
      return entry?.canonical_answer_id ?? null;
    });
    expect(answerId, "seed-e2e must create e2e-motor / E2E sample answer").toBeTruthy();

    await page.goto(`/answers/${answerId}`);
    const star = page.locator('[data-testid="bookmark-button"]:visible');
    await expect(star).toBeVisible({ timeout: 15_000 });
    // BookmarkButton stays disabled until the initial listBookmarks hydrate finishes.
    await expect(star).toBeEnabled({ timeout: 15_000 });

    async function clickStarAndWait(expectedLabel) {
      const toggleWait = page.waitForResponse(
        (res) =>
          res.url().includes("/api/bookmarks/toggle") &&
          res.request().method() === "POST" &&
          res.ok()
      );
      await star.click({ force: true, delay: 100 });
      await toggleWait;
      await expect(star).toHaveAttribute("aria-label", expectedLabel, { timeout: 10_000 });
    }

    // Idempotent: flip whatever the current state is, waiting on the network each time.
    const starBefore = await star.getAttribute("aria-label");
    expect(
      starBefore === "Bookmark for later" || starBefore === "Remove bookmark"
    ).toBeTruthy();
    const afterFirst =
      starBefore === "Bookmark for later" ? "Remove bookmark" : "Bookmark for later";
    await clickStarAndWait(afterFirst);

    // Ensure a bookmark exists for the list assertion.
    if ((await star.getAttribute("aria-label")) === "Bookmark for later") {
      await clickStarAndWait("Remove bookmark");
    }

    await page.goto("/bookmarks");
    await expect(page.getByRole("heading", { level: 1, name: "Bookmarks" })).toBeVisible();
    await expect(page.getByRole("link", { name: new RegExp(`Answer #${answerId}`) })).toBeVisible();
  });
});
