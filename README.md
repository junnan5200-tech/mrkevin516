# Twitter -> 币安广场自动同步服务

这个项目用于在你发布新的 X/Twitter 推文后，尽快同步到币安广场。

当前实现采用两段式方案：

1. **推文发现**：支持 `X Webhook` 或 `定时轮询 X API`
2. **币安广场发布**：由于没有明确公开的官方发帖 API，使用 **Playwright 浏览器自动化** 复用已登录的币安会话完成发帖

## 功能特性

- 支持 X webhook（适合有 Account Activity / Webhook 能力的场景）
- 支持轮询 X API（默认模式，更容易落地）
- 自动去重，避免同一条推文重复同步
- 可选追加推文原文链接到币安广场内容末尾
- 支持手动触发一次最新推文同步
- 支持 `BINANCE_DRY_RUN=true` 进行联调，不真正发帖

## 目录结构

```text
src/
  config.js              配置读取
  twitter.js             X API 与 webhook 解析
  binance-square.js      币安广场自动发帖
  store.js               本地状态存储
  sync-service.js        同步编排
  index.js               HTTP 服务入口
scripts/
  binance-login.js       首次登录币安并保存会话
test/
  *.test.js              基础单元测试
```

## 安装

```bash
npm install
```

如果是首次在当前机器运行 Playwright，通常还需要安装 Chromium：

```bash
npx playwright install chromium
```

## 配置

先复制环境变量模板：

```bash
cp .env.example .env
```

关键配置如下：

### X / Twitter

- `SYNC_MODE=poll|webhook|both`
- `TWITTER_BEARER_TOKEN`：X API Bearer Token
- `TWITTER_USER_ID`：你的 X 用户 ID
- `TWITTER_USERNAME`：你的 X 用户名，不带 `@`
- `TWITTER_CONSUMER_SECRET`：仅 webhook CRC 校验需要
- `TWITTER_POLL_INTERVAL_MS`：轮询间隔，默认 60000

### Binance Square

- `BINANCE_STORAGE_STATE_PATH`：保存币安登录态的文件
- `BINANCE_HEADLESS=true|false`
- `BINANCE_DRY_RUN=true|false`
- `BINANCE_APPEND_SOURCE_LINK=true|false`

## 首次保存币安登录态

币安常见验证码、二次验证、风控等流程不适合硬编码自动登录，因此这里采用**手动登录一次，后续复用会话**的方式。

执行：

```bash
npm run binance:login
```

脚本会打开浏览器，请手动完成：

1. 登录币安
2. 进入币安广场发帖页
3. 回到终端按回车

然后会把登录态保存到 `.data/binance-storage.json`（或你自定义的路径）。

## 启动服务

```bash
npm start
```

默认会启动在：

```text
http://localhost:3000
```

## API

### 健康检查

```http
GET /health
```

### X Webhook CRC 校验

```http
GET /webhooks/x?crc_token=...
```

### 接收 X Webhook 事件

```http
POST /webhooks/x
Content-Type: application/json
```

### 手动同步一次最新推文

```http
POST /sync/twitter/latest
x-api-key: <SYNC_API_KEY>
```

如果没有设置 `SYNC_API_KEY`，则该接口默认不鉴权。

## 轮询模式工作方式

- 服务启动后会读取本地状态文件 `.data/state.json`
- 如果是第一次运行，并且 `TWITTER_SKIP_INITIAL_BACKFILL=true`
  - 不会把历史推文全部补发到币安广场
  - 只会记住当前最新推文 ID，从下一条新推文开始同步
- 后续每次轮询只拉取新的推文并同步

## 测试

```bash
npm test
```

## 注意事项

1. **币安广场目前没有在本仓库内接入官方发帖 API**，当前实现依赖网页自动化。
2. 网页结构可能变化，如果发布失败，请优先检查 `src/binance-square.js` 里的输入框和发布按钮选择器。
3. 请自行确认此自动化流程是否符合 X 和 Binance 的平台规则与账号风控要求。
4. 建议先使用 `BINANCE_DRY_RUN=true` 验证推文发现与去重逻辑，再切换到真实发布。