import fs from "node:fs/promises";
import path from "node:path";

const EMPTY_STATE = {
  syncedTweetIds: [],
  lastSeenTweetId: "",
};

export class JsonStateStore {
  constructor(filePath) {
    this.filePath = filePath;
  }

  async ensureFile() {
    await fs.mkdir(path.dirname(this.filePath), { recursive: true });

    try {
      await fs.access(this.filePath);
    } catch {
      await fs.writeFile(this.filePath, JSON.stringify(EMPTY_STATE, null, 2));
    }
  }

  async readState() {
    await this.ensureFile();
    const content = await fs.readFile(this.filePath, "utf8");

    if (!content.trim()) {
      return { ...EMPTY_STATE };
    }

    const parsedState = JSON.parse(content);

    return {
      syncedTweetIds: Array.isArray(parsedState.syncedTweetIds)
        ? parsedState.syncedTweetIds
        : [],
      lastSeenTweetId: parsedState.lastSeenTweetId ?? "",
    };
  }

  async writeState(state) {
    await this.ensureFile();
    await fs.writeFile(this.filePath, JSON.stringify(state, null, 2));
  }

  async hasSynced(tweetId) {
    const state = await this.readState();
    return state.syncedTweetIds.includes(tweetId);
  }

  async rememberSynced(tweetId) {
    const state = await this.readState();

    if (!state.syncedTweetIds.includes(tweetId)) {
      state.syncedTweetIds.push(tweetId);
    }

    if (!state.lastSeenTweetId || compareTweetIds(tweetId, state.lastSeenTweetId) > 0) {
      state.lastSeenTweetId = tweetId;
    }

    await this.writeState(state);
  }

  async getLastSeenTweetId() {
    const state = await this.readState();
    return state.lastSeenTweetId;
  }

  async setLastSeenTweetId(tweetId) {
    const state = await this.readState();
    state.lastSeenTweetId = tweetId;
    await this.writeState(state);
  }
}

export function compareTweetIds(left, right) {
  if (!left && !right) {
    return 0;
  }

  if (!left) {
    return -1;
  }

  if (!right) {
    return 1;
  }

  try {
    const leftId = BigInt(left);
    const rightId = BigInt(right);

    if (leftId === rightId) {
      return 0;
    }

    return leftId > rightId ? 1 : -1;
  } catch {
    return left.localeCompare(right);
  }
}
