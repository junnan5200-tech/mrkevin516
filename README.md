# 推特加密情绪指标 vs BTC走势 — 相关性与套利分析

## 概述

本项目分析 Twitter/X 上加密货币情绪指标（Fear & Greed Index）与比特币价格走势之间的相关性，并回测基于情绪的交易策略，评估是否存在可利用的套利机会。

## 数据来源

- **Crypto Fear & Greed Index** — [alternative.me API](https://alternative.me/crypto/fear-and-greed-index/)（综合推特情绪、搜索量、波动率、交易量等因子）
- **BTC 历史价格** — CoinGecko API（需要API Key；无Key时使用模拟数据）

## 分析内容

1. **相关性分析** — 皮尔逊/斯皮尔曼相关系数
2. **领先/滞后分析** — 交叉相关性检验情绪是否领先价格
3. **极端情绪统计** — 极度恐惧/贪婪后的收益分布
4. **逆向情绪策略回测** — 恐惧时买入、贪婪时卖出
5. **情绪动量策略回测** — 基于情绪变化速度的交易策略
6. **可视化** — 6张综合分析图表

## 使用方法

```bash
pip install pandas numpy matplotlib seaborn requests scipy scikit-learn
python3 crypto_sentiment_analysis.py
```

## 输出文件

- `crypto_sentiment_analysis.png` — 综合分析图表
- `crypto_sentiment_data.csv` — 合并后的原始数据

## 依赖

- Python 3.10+
- pandas, numpy, matplotlib, seaborn, requests, scipy, scikit-learn
