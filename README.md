# 推特加密情绪指标 vs BTC走势 — 相关性与套利分析

## 概述

本项目包含两个核心模块：
1. **Fear & Greed Index 与 BTC 价格的定量相关性分析** — 证明极端恐惧时存在逆向套利机会
2. **加密推特 KOL 情绪监控 & 极端悲观套利信号系统** — 精选27个KOL账号，通过其推文情绪判断市场极端状态

## 模块说明

### 模块一: `crypto_sentiment_analysis.py`
- 获取 Fear & Greed Index 历史数据 + BTC 价格
- 皮尔逊/斯皮尔曼相关性分析
- 领先/滞后交叉相关性检验
- 极端情绪区间的未来收益统计
- 逆向情绪策略 & 动量策略回测
- 生成6张综合可视化图表

### 模块二: `kol_sentiment_monitor.py`
- 27个精选KOL档案（分4个梯队，含入选理由和反向指标价值评级）
- 加密专用NLP情绪关键词库（中英文双语）
- 加权情绪聚合引擎
- 极端悲观信号检测 & 逆向买入规则
- KOL名单导出为JSON（`kol_watchlist.json`）

## 使用方法

```bash
pip install -r requirements.txt

# 运行相关性分析
python3 crypto_sentiment_analysis.py

# 运行KOL情绪监控系统（演示模式）
python3 kol_sentiment_monitor.py
```

## KOL名单结构

| 梯队 | 反向指标价值 | 代表账号 | 用途 |
|------|------------|---------|------|
| 第一梯队 | 极高 | @CryptoCapo_, @AltcoinGordon, @100trillionUSD | 极端悲观时最强逆向信号 |
| 第二梯队 | 高 | @CryptoMichNL, @PeterLBrandt, @DonAlt, @inversebrah | 情绪转向有强参考意义 |
| 第三梯队 | 中等 | @woonomic, @glassnode, @LookOnChain | 数据驱动佐证 |
| 第四梯队 | 辅助 | @saylor | 极端环境佐证 |

## 输出文件

- `crypto_sentiment_analysis.png` — 综合分析图表
- `crypto_sentiment_data.csv` — 合并后的原始数据
- `kol_watchlist.json` — KOL名单（供程序使用）

## 依赖

- Python 3.10+
- pandas, numpy, matplotlib, seaborn, requests, scipy, scikit-learn
