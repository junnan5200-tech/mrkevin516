import { interactiveBinanceLogin } from "../src/binance-square.js";
import { config } from "../src/config.js";

interactiveBinanceLogin(config.binance).catch((error) => {
  console.error("保存币安登录会话失败", error);
  process.exit(1);
});
