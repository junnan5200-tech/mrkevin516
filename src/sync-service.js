import { buildBinanceSquareContent } from "./text.js";

export class SyncService {
  constructor({ publisher, stateStore, binanceConfig, twitterConfig }) {
    this.publisher = publisher;
    this.stateStore = stateStore;
    this.binanceConfig = binanceConfig;
    this.twitterConfig = twitterConfig;
    this.syncInProgress = false;
  }

  async syncTweets(tweets) {
    if (this.syncInProgress) {
      console.log("上一次同步尚未结束，本次跳过");
      return { syncedCount: 0, skippedCount: tweets.length };
    }

    this.syncInProgress = true;

    try {
      let syncedCount = 0;
      let skippedCount = 0;

      for (const tweet of tweets) {
        const alreadySynced = await this.stateStore.hasSynced(tweet.id);

        if (alreadySynced) {
          skippedCount += 1;
          continue;
        }

        const content = buildBinanceSquareContent(tweet, {
          appendSourceLink: this.binanceConfig.appendSourceLink,
          maxLength: this.binanceConfig.maxPostLength,
        });

        await this.publisher.publishPost(content);
        await this.stateStore.rememberSynced(tweet.id);

        syncedCount += 1;
        console.log(`已同步推文 ${tweet.id} 到币安广场`);
      }

      return { syncedCount, skippedCount };
    } finally {
      this.syncInProgress = false;
    }
  }

  async initializeLastSeen(tweetId) {
    if (!tweetId) {
      return;
    }

    const lastSeenTweetId = await this.stateStore.getLastSeenTweetId();

    if (!lastSeenTweetId) {
      await this.stateStore.setLastSeenTweetId(tweetId);
    }
  }

  async markLastSeen(tweetId) {
    if (!tweetId) {
      return;
    }

    await this.stateStore.setLastSeenTweetId(tweetId);
  }

  async getLastSeenTweetId() {
    return this.stateStore.getLastSeenTweetId();
  }
}
