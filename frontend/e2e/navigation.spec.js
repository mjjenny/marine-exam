import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

/**
 * Locators mirrored from App.jsx HeaderNav + AdminMobileNav.jsx:
 *   <nav className="header-nav" aria-label="Desktop">...</nav>
 *   <nav className="admin-mobile-nav mobile-only" aria-label="Admin">...</nav>
 *
 * CSS hides desktop header below 48rem and hides AdminMobileNav above it
 * (display:none). Playwright getByRole ignores display:none nodes by default,
 * so "not shown" is asserted with toHaveCount(0), not toBeHidden().
 */
test.describe("Responsive navigation", () => {
  test("desktop shows header nav with Members; mobile admin strip is hidden", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "Desktop Chrome", "Desktop Chrome project only");

    await loginAs(page, USERS.admin);
    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { level: 1, name: "Members" })).toBeVisible();

    // aria-label="Desktop" on HeaderNav <nav> in App.jsx
    const desktopNav = page.getByRole("navigation", { name: "Desktop" });
    await expect(desktopNav).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Members", exact: true })).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Approvals", exact: true })).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Moderation", exact: true })).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Add Diet", exact: true })).toBeVisible();

    // aria-label="Admin" nav is display:none on desktop -> not in a11y tree
    await expect(page.getByRole("navigation", { name: "Admin" })).toHaveCount(0);
  });

  test("mobile shows AdminMobileNav with Members; desktop header is hidden", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "Mobile Safari", "Mobile Safari project only");

    await loginAs(page, USERS.admin);
    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { level: 1, name: "Members" })).toBeVisible();

    // aria-label="Desktop" nav is inside .desktop-only header -> display:none on mobile
    await expect(page.getByRole("navigation", { name: "Desktop" })).toHaveCount(0);

    // aria-label="Admin" on AdminMobileNav.jsx <nav>
    const adminNav = page.getByRole("navigation", { name: "Admin" });
    await expect(adminNav).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Members", exact: true })).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Approvals", exact: true })).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Moderation", exact: true })).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Add Diet", exact: true })).toBeVisible();

    // theme.css: .admin-mobile-nav { overflow-x: auto } inside the mobile media query
    const overflowX = await adminNav.evaluate((el) => getComputedStyle(el).overflowX);
    expect(overflowX).toBe("auto");
  });
});
