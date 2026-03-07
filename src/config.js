import dotenv from "dotenv";
import path from "node:path";

dotenv.config();

const workspaceRoot = process.cwd();

function readBoolean(name, defaultValue = false) {
  const rawValue = process.env[name];

  if (rawValue === undefined) {
    return defaultValue;
  }

  return ["1", "true", "yes", "on"].includes(rawValue.toLowerCase());
}

function readNumber(name, defaultValue) {
  const rawValue = process.env[name];

  if (rawValue === undefined) {
    return defaultValue;
  }

  const parsedValue = Number(rawValue);

  if (Number.isNaN(parsedValue)) {
    throw new Error(`环境变量 ${name} 不是有效数字`);
  }

  return parsedValue;
}

function resolveWorkspacePath(value, fallbackRelativePath) {
  const target = value ?? fallbackRelativePath;
  return path.isAbsolute(target) ? target : path.join(workspaceRoot, target);
}

export const config = {
  server: {
    port: readNumber("PORT", 3000),
    syncMode: process.env.SYNC_MODE ?? "poll",
    apiKey: process.env.SYNC_API_KEY ?? "",
  },
  polling: {
    intervalMs: readNumber("TWITTER_POLL_INTERVAL_MS", 60_000),
    skipInitialBackfill: readBoolean("TWITTER_SKIP_INITIAL_BACKFILL", true),
    runImmediately: readBoolean("TWITTER_POLL_RUN_IMMEDIATELY", true),
  },
  twitter: {
    apiBaseUrl: process.env.TWITTER_API_BASE_URL ?? "https://api.x.com/2",
    bearerToken: process.env.TWITTER_BEARER_TOKEN ?? "",
    userId: process.env.TWITTER_USER_ID ?? "",
    username: process.env.TWITTER_USERNAME ?? "",
    consumerSecret: process.env.TWITTER_CONSUMER_SECRET ?? "",
  },
  binance: {
    baseUrl: process.env.BINANCE_BASE_URL ?? "https://www.binance.com",
    composeUrl:
      process.env.BINANCE_COMPOSE_URL ?? "https://www.binance.com/en/square/post",
    storageStatePath: resolveWorkspacePath(
      process.env.BINANCE_STORAGE_STATE_PATH,
      ".data/binance-storage.json",
    ),
    headless: readBoolean("BINANCE_HEADLESS", true),
    dryRun: readBoolean("BINANCE_DRY_RUN", false),
    appendSourceLink: readBoolean("BINANCE_APPEND_SOURCE_LINK", true),
    maxPostLength: readNumber("BINANCE_MAX_POST_LENGTH", 10_000),
  },
  state: {
    filePath: resolveWorkspacePath(process.env.STATE_FILE_PATH, ".data/state.json"),
  },
};

export function validatePollingConfig() {
  const missing = [];

  if (!config.twitter.bearerToken) {
    missing.push("TWITTER_BEARER_TOKEN");
  }

  if (!config.twitter.userId) {
    missing.push("TWITTER_USER_ID");
  }

  if (!config.twitter.username) {
    missing.push("TWITTER_USERNAME");
  }

  if (missing.length > 0) {
    throw new Error(`轮询模式缺少环境变量: ${missing.join(", ")}`);
  }
}

export function validateWebhookConfig() {
  if (!config.twitter.username) {
    throw new Error("Webhook 模式至少需要配置 TWITTER_USERNAME");
  }
}

export function validatePublisherConfig() {
  if (config.binance.dryRun) {
    return;
  }

  if (!config.binance.storageStatePath) {
    throw new Error("缺少 BINANCE_STORAGE_STATE_PATH");
  }
}
