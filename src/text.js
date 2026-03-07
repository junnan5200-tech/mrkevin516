export function normalizeWhitespace(value) {
  return (value ?? "").replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

export function truncateWithSuffix(text, maxLength, suffix = "...") {
  if (text.length <= maxLength) {
    return text;
  }

  const sliceLength = Math.max(0, maxLength - suffix.length);
  return `${text.slice(0, sliceLength).trimEnd()}${suffix}`;
}

export function buildTweetUrl(username, tweetId) {
  return `https://x.com/${username}/status/${tweetId}`;
}

export function buildBinanceSquareContent(tweet, options = {}) {
  const {
    appendSourceLink = true,
    maxLength = 10_000,
  } = options;

  const text = normalizeWhitespace(tweet.text);
  const sourceUrl = tweet.url ?? buildTweetUrl(tweet.username, tweet.id);
  const footer = appendSourceLink ? `\n\n来源：${sourceUrl}` : "";
  const allowedTextLength = maxLength - footer.length;
  const safeText = truncateWithSuffix(text, allowedTextLength);

  return `${safeText}${footer}`.trim();
}
