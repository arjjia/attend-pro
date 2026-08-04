import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Университетская почта").fill(email);
  await page.getByLabel("Пароль").fill("123456");
  await page.getByRole("button", { name: "Войти" }).click();
}

test("lecturer starts attendance and receives a student mark", async ({ browser, page }) => {
  await login(page, "lecturer@test.ru");
  await expect(page.getByRole("heading", { name: "Расписание преподавателя" })).toBeVisible();

  const [widget] = await Promise.all([
    page.waitForEvent("popup"),
    page.getByRole("button", { name: /Начать занятие|Открыть виджет/ }).click(),
  ]);
  const code = widget.locator(".giant-code");
  await expect(code).toHaveText(/^\d{6}$/);
  const currentCode = (await code.textContent()) || "";
  await expect(widget.locator(".attendance-stage")).toBeVisible();
  await widget.waitForTimeout(300);
  const alreadyMarked = await widget.getByText("Иванов Иван").isVisible().catch(() => false);

  const studentContext = await browser.newContext();
  const studentPage = await studentContext.newPage();
  await login(studentPage, "student1@test.ru");
  await expect(studentPage.getByRole("heading", { name: "Мои занятия" })).toBeVisible();
  if (alreadyMarked) {
    await studentPage.getByRole("link", { name: "История" }).click();
    await expect(studentPage.getByRole("cell", { name: "Зачтено" })).toBeVisible();
  } else {
    await studentPage.getByRole("button", { name: "Отметить присутствие" }).click();
    await studentPage.getByLabel("Шестизначный код с экрана преподавателя").fill(currentCode);
    await studentPage.getByRole("button", { name: "Подтвердить присутствие" }).click();
    await expect(studentPage.getByRole("heading", { name: "Присутствие отмечено" })).toBeVisible();
  }

  await expect(widget.getByText("Иванов Иван")).toBeVisible();
  widget.on("dialog", (dialog) => dialog.accept());
  await widget.getByRole("button", { name: "Завершить занятие" }).click();
  await expect(widget.getByRole("heading", { name: "Отметка присутствия закрыта" })).toBeVisible();

  await studentContext.close();
});
