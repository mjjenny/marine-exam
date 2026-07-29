import { test, expect } from "@playwright/test";
import { USERS, loginAs } from "./helpers.js";

test.describe("Responsive navigation", () => {
  test("desktop shows header nav with Members; mobile admin strip is hidden", async ({
    page,
    isMobile,
  }) => {
    test.skip(isMobile, "Desktop Chrome project only");
    await loginAs(page, USERS.admin);
    await page.goto("/admin/users");

    const desktopNav = page.getByRole("navigation", { name: "Desktop" });
    await expect(desktopNav).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Members" })).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Approvals" })).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Moderation" })).toBeVisible();
    await expect(desktopNav.getByRole("link", { name: "Add Diet" })).toBeVisible();

    // Admin mobile strip must not show on desktop viewports.
    await expect(page.getByRole("navigation", { name: "Admin" })).toBeHidden();
  });

  test("mobile shows AdminMobileNav with Members; desktop header is hidden", async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, "Mobile Safari project only");
    await loginAs(page, USERS.admin);
    await page.goto("/admin/users");

    await expect(page.getByRole("navigation", { name: "Desktop" })).toBeHidden();

    const adminNav = page.getByRole("navigation", { name: "Admin" });
    await expect(adminNav).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Members" })).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Approvals" })).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Moderation" })).toBeVisible();
    await expect(adminNav.getByRole("link", { name: "Add Diet" })).toBeVisible();

    // Horizontally scrollable strip (overflow-x: auto).
    await expect(adminNav).toHaveCSS("overflow-x", /auto|scroll/);
  });
});
