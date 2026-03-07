import fs from "node:fs/promises";
import path from "node:path";

import { chromium } from "playwright";

const EDITOR_SELECTORS = [
  "[contenteditable=\"true\"]",
  "div[role=\"textbox\"]",
  "textarea",
];

const PUBLISH_BUTTON_TEXTS = [
  /post/i,
  /publish/i,
  /share/i,
  /发布/,
  /发表/,
  /分享/,
];

export class BinanceSquarePublisher {
  constructor(config) {
    this.config = config;
  }

  async publishPost(content) {
    if (this.config.dryRun) {
      console.log(`[dry-run] 已跳过币安广场发布:\n${content}`);
      return;
    }

    await assertStorageStateExists(this.config.storageStatePath);

    const browser = await chromium.launch({
      headless: this.config.headless,
    });

    const context = await browser.newContext({
      storageState: this.config.storageStatePath,
    });

    const page = await context.newPage();

    try {
      await page.goto(this.config.composeUrl, {
        waitUntil: "domcontentloaded",
        timeout: 60_000,
      });

      await ensureLoggedIn(page);
      const editor = await locateEditor(page);
      await fillEditor(page, editor, content);
      const publishButton = await locatePublishButton(page);
      await publishButton.click();

      await page.waitForTimeout(4_000);
    } finally {
      await context.close();
      await browser.close();
    }
  }
}

export async function interactiveBinanceLogin(config) {
  const browser = await chromium.launch({
    headless: false,
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(config.composeUrl, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    console.log("请在打开的浏览器中完成币安登录，并进入币安广场发帖页。");
    console.log("登录完成后回到终端按回车，将当前会话保存到 storageState 文件。");

    await waitForEnter();

    await fs.mkdir(path.dirname(config.storageStatePath), { recursive: true });

    await context.storageState({ path: config.storageStatePath });
    console.log(`会话已保存到 ${config.storageStatePath}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

async function ensureLoggedIn(page) {
  const currentUrl = page.url();

  if (/login|sign-in|signin/i.test(currentUrl)) {
    throw new Error("当前会话未登录币安，请先执行 npm run binance:login");
  }

  const signInButton = page
    .getByRole("button", { name: /sign in|log in|登录/i })
    .first();

  if (await signInButton.isVisible().catch(() => false)) {
    throw new Error("检测到登录入口，当前 storageState 可能已失效，请重新登录");
  }
}

async function locateEditor(page) {
  for (const selector of EDITOR_SELECTORS) {
    const locator = page.locator(selector).first();
    const visible = await locator.isVisible({ timeout: 2_000 }).catch(() => false);

    if (visible) {
      return locator;
    }
  }

  throw new Error("未找到币安广场发帖输入框，请检查页面结构是否变化");
}

async function fillEditor(page, editor, content) {
  await editor.click();

  const tagName = await editor.evaluate((node) => node.tagName.toLowerCase());

  if (tagName === "textarea") {
    await editor.fill(content);
    return;
  }

  await editor.evaluate((node) => {
    if ("innerHTML" in node) {
      node.innerHTML = "";
    }
  });

  await page.keyboard.insertText(content);
}

async function locatePublishButton(page) {
  for (const textPattern of PUBLISH_BUTTON_TEXTS) {
    const locator = page.getByRole("button", { name: textPattern }).first();
    const visible = await locator.isVisible({ timeout: 1_500 }).catch(() => false);

    if (visible) {
      return locator;
    }
  }

  const genericButton = page.locator("button").last();
  if (await genericButton.isVisible({ timeout: 1_000 }).catch(() => false)) {
    return genericButton;
  }

  throw new Error("未找到币安广场发布按钮，请检查页面结构是否变化");
}

async function assertStorageStateExists(filePath) {
  try {
    await fs.access(filePath);
  } catch {
    throw new Error(
      `未找到币安登录会话文件 ${filePath}，请先执行 npm run binance:login`,
    );
  }
}

function waitForEnter() {
  return new Promise((resolve) => {
    process.stdin.resume();
    process.stdout.write("> ");
    process.stdin.once("data", () => {
      process.stdin.pause();
      resolve();
    });
  });
}
