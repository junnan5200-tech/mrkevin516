import crypto from "node:crypto";

import { compareTweetIds } from "./store.js";
import { buildTweetUrl, normalizeWhitespace } from "./text.js";

export class TwitterClient {
  constructor(config) {
    this.config = config;
  }

  async fetchLatestTweets({ sinceId } = {}) {
    const params = new URLSearchParams({
      max_results: "10",
      exclude: "retweets,replies",
      "tweet.fields": "created_at",
    });

    if (sinceId) {
      params.set("since_id", sinceId);
    }

    const response = await fetch(
      `${this.config.apiBaseUrl}/users/${this.config.userId}/tweets?${params.toString()}`,
      {
        headers: {
          Authorization: `Bearer ${this.config.bearerToken}`,
        },
      },
    );

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`拉取推文失败: ${response.status} ${errorBody}`);
    }

    const payload = await response.json();
    const tweets = Array.isArray(payload.data) ? payload.data : [];

    return tweets
      .map((tweet) => normalizeApiTweet(tweet, this.config.username))
      .sort((left, right) => compareTweetIds(left.id, right.id));
  }
}

export function normalizeApiTweet(tweet, username) {
  return {
    id: String(tweet.id),
    text: normalizeWhitespace(tweet.text),
    createdAt: tweet.created_at ?? null,
    username,
    url: buildTweetUrl(username, tweet.id),
    source: "polling",
  };
}

export function extractTweetsFromWebhook(payload, options = {}) {
  const username = options.username ?? "";
  const expectedUserId = options.userId ?? "";
  const events = [
    ...(Array.isArray(payload?.tweet_create_events) ? payload.tweet_create_events : []),
    ...(Array.isArray(payload?.tweet_create_event) ? payload.tweet_create_event : []),
  ];

  return events
    .filter((event) => isEligibleTweetEvent(event, expectedUserId))
    .map((event) => ({
      id: String(event.id_str ?? event.id),
      text: normalizeWhitespace(event.full_text ?? event.text),
      createdAt: event.created_at ?? null,
      username,
      url: buildTweetUrl(username, event.id_str ?? event.id),
      source: "webhook",
    }))
    .sort((left, right) => compareTweetIds(left.id, right.id));
}

export function buildCrcResponseToken(crcToken, consumerSecret) {
  const digest = crypto
    .createHmac("sha256", consumerSecret)
    .update(crcToken)
    .digest("base64");

  return `sha256=${digest}`;
}

export function isValidWebhookSignature(rawBody, signature, consumerSecret) {
  if (!signature || !consumerSecret) {
    return false;
  }

  const expectedSignature = `sha256=${crypto
    .createHmac("sha256", consumerSecret)
    .update(rawBody)
    .digest("base64")}`;

  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expectedSignature);

  if (actualBuffer.length !== expectedBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(actualBuffer, expectedBuffer);
}

function isEligibleTweetEvent(event, expectedUserId) {
  const authorId =
    event?.user?.id_str ??
    event?.user?.id ??
    event?.user_id ??
    event?.user_id_str ??
    "";

  const isSelfAuthored = !expectedUserId || String(authorId) === String(expectedUserId);
  const isRetweet = Boolean(event?.retweeted_status) || String(event?.full_text ?? event?.text ?? "").startsWith("RT @");
  const isReply =
    Boolean(event?.in_reply_to_status_id) || Boolean(event?.in_reply_to_status_id_str);

  return isSelfAuthored && !isRetweet && !isReply;
}
