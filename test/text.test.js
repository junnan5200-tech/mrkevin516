import test from "node:test";
import assert from "node:assert/strict";

import { buildBinanceSquareContent, truncateWithSuffix } from "../src/text.js";

test("buildBinanceSquareContent appends source link", () => {
  const content = buildBinanceSquareContent(
    {
      id: "123",
      username: "alice",
      text: "hello world",
    },
    {
      appendSourceLink: true,
      maxLength: 100,
    },
  );

  assert.equal(content, "hello world\n\n来源：https://x.com/alice/status/123");
});

test("buildBinanceSquareContent truncates body but keeps footer", () => {
  const content = buildBinanceSquareContent(
    {
      id: "123",
      username: "alice",
      text: "12345678901234567890",
    },
    {
      appendSourceLink: true,
      maxLength: 40,
    },
  );

  assert.ok(content.endsWith("来源：https://x.com/alice/status/123"));
  assert.ok(content.includes("..."));
});

test("truncateWithSuffix keeps short strings intact", () => {
  assert.equal(truncateWithSuffix("abc", 10), "abc");
});
