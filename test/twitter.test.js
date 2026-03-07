import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCrcResponseToken,
  extractTweetsFromWebhook,
  isValidWebhookSignature,
} from "../src/twitter.js";

test("extractTweetsFromWebhook filters retweets and replies", () => {
  const tweets = extractTweetsFromWebhook(
    {
      tweet_create_events: [
        {
          id_str: "2",
          full_text: "normal tweet",
          user: { id_str: "42" },
        },
        {
          id_str: "3",
          full_text: "RT @bob hi",
          user: { id_str: "42" },
        },
        {
          id_str: "4",
          full_text: "reply",
          user: { id_str: "42" },
          in_reply_to_status_id_str: "1",
        },
      ],
    },
    {
      username: "alice",
      userId: "42",
    },
  );

  assert.deepEqual(tweets.map((tweet) => tweet.id), ["2"]);
  assert.equal(tweets[0].url, "https://x.com/alice/status/2");
});

test("buildCrcResponseToken returns x compatible prefix", () => {
  const token = buildCrcResponseToken("abc", "secret");
  assert.ok(token.startsWith("sha256="));
});

test("isValidWebhookSignature validates request body hmac", () => {
  const body = Buffer.from(JSON.stringify({ hello: "world" }));
  const signature = buildCrcResponseToken(body, "secret");
  assert.equal(isValidWebhookSignature(body, signature, "secret"), true);
});
