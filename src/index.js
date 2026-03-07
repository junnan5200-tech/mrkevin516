import express from "express";

import { BinanceSquarePublisher } from "./binance-square.js";
import { config, validatePollingConfig, validatePublisherConfig, validateWebhookConfig } from "./config.js";
import { JsonStateStore } from "./store.js";
import { SyncService } from "./sync-service.js";
import {
  buildCrcResponseToken,
  extractTweetsFromWebhook,
  isValidWebhookSignature,
  TwitterClient,
} from "./twitter.js";

const app = express();
app.use(
  express.json({
    limit: "1mb",
    verify(request, _response, buffer) {
      request.rawBody = buffer;
    },
  }),
);

const stateStore = new JsonStateStore(config.state.filePath);
const publisher = new BinanceSquarePublisher(config.binance);
const syncService = new SyncService({
  publisher,
  stateStore,
  binanceConfig: config.binance,
  twitterConfig: config.twitter,
});

let twitterClient = null;
let pollTimer = null;

app.get("/health", async (_request, response) => {
  response.json({
    ok: true,
    mode: config.server.syncMode,
    lastSeenTweetId: await syncService.getLastSeenTweetId(),
  });
});

app.get("/webhooks/x", (request, response) => {
  const { crc_token: crcToken } = request.query;

  if (!crcToken || typeof crcToken !== "string") {
    response.status(400).json({ error: "missing crc_token" });
    return;
  }

  if (!config.twitter.consumerSecret) {
    response.status(500).json({ error: "missing TWITTER_CONSUMER_SECRET" });
    return;
  }

  response.json({
    response_token: buildCrcResponseToken(crcToken, config.twitter.consumerSecret),
  });
});

app.post("/webhooks/x", async (request, response) => {
  const signature = request.get("x-twitter-webhooks-signature");

  if (config.twitter.consumerSecret) {
    if (!signature) {
      response.status(401).json({ error: "missing webhook signature" });
      return;
    }

    if (!isValidWebhookSignature(request.rawBody, signature, config.twitter.consumerSecret)) {
      response.status(401).json({ error: "invalid webhook signature" });
      return;
    }
  }

  response.status(202).json({ accepted: true });

  const tweets = extractTweetsFromWebhook(request.body, {
    username: config.twitter.username,
    userId: config.twitter.userId,
  });

  if (tweets.length === 0) {
    return;
  }

  try {
    await syncService.syncTweets(tweets);
    await syncService.markLastSeen(tweets.at(-1)?.id);
  } catch (error) {
    console.error("处理 webhook 推文失败", error);
  }
});

app.post("/sync/twitter/latest", async (request, response) => {
  if (!hasValidApiKey(request.get("x-api-key"))) {
    response.status(401).json({ error: "unauthorized" });
    return;
  }

  if (!twitterClient) {
    response.status(400).json({ error: "polling mode is not enabled" });
    return;
  }

  try {
    const result = await syncLatestTweets();
    response.json(result);
  } catch (error) {
    response.status(500).json({ error: error.message });
  }
});

async function bootstrap() {
  validatePublisherConfig();

  if (supportsWebhookMode(config.server.syncMode)) {
    validateWebhookConfig();
  }

  if (supportsPollingMode(config.server.syncMode)) {
    validatePollingConfig();
    twitterClient = new TwitterClient(config.twitter);

    if (config.polling.runImmediately) {
      await syncLatestTweets();
    }

    pollTimer = setInterval(() => {
      syncLatestTweets().catch((error) => {
        console.error("轮询推特失败", error);
      });
    }, config.polling.intervalMs);
  }

  app.listen(config.server.port, () => {
    console.log(
      `同步服务已启动: http://0.0.0.0:${config.server.port} (mode=${config.server.syncMode})`,
    );
  });
}

async function syncLatestTweets() {
  const lastSeenTweetId = await syncService.getLastSeenTweetId();
  const tweets = await twitterClient.fetchLatestTweets({
    sinceId: lastSeenTweetId || undefined,
  });

  if (tweets.length === 0) {
    return {
      syncedCount: 0,
      skippedCount: 0,
      reason: "no_new_tweets",
    };
  }

  if (!lastSeenTweetId && config.polling.skipInitialBackfill) {
    const newestTweetId = tweets.at(-1)?.id;
    await syncService.initializeLastSeen(newestTweetId);

    return {
      syncedCount: 0,
      skippedCount: tweets.length,
      reason: "initial_backfill_skipped",
    };
  }

  const result = await syncService.syncTweets(tweets);
  await syncService.markLastSeen(tweets.at(-1)?.id);
  return result;
}

function hasValidApiKey(apiKey) {
  if (!config.server.apiKey) {
    return true;
  }

  return apiKey === config.server.apiKey;
}

function supportsPollingMode(mode) {
  return mode === "poll" || mode === "both";
}

function supportsWebhookMode(mode) {
  return mode === "webhook" || mode === "both";
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

function shutdown() {
  if (pollTimer) {
    clearInterval(pollTimer);
  }

  process.exit(0);
}

bootstrap().catch((error) => {
  console.error("服务启动失败", error);
  process.exit(1);
});
