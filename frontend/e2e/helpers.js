/** Shared E2E credentials — created by `flask seed-e2e`. */
export const USERS = {
  admin: { email: "admin@e2e.local", password: "E2eAdmin1!" },
  member: { email: "member@e2e.local", password: "E2eMember1!" },
  revoked: { email: "revoked@e2e.local", password: "E2eRevoked1!" },
  searchable: { email: "searchable@e2e.local", password: "E2eSearch1!" },
};

export async function loginAs(page, { email, password }) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /^Log in$/i }).click();
}
