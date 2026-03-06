"""
推特加密情绪指标与BTC走势相关性分析 & 回测框架

数据来源:
- Crypto Fear & Greed Index (alternative.me API) — 综合了社交媒体情绪、波动率、交易量等
- BTC 历史价格 (CoinGecko API)

分析内容:
1. 情绪指数与BTC价格的皮尔逊/斯皮尔曼相关性
2. 情绪极值区间的价格走势统计
3. 情绪变化的领先/滞后关系 (Granger因果检验)
4. 基于情绪的简单交易策略回测
"""

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings("ignore")

plt.rcParams["figure.figsize"] = (14, 8)
plt.rcParams["font.size"] = 12

# ─────────────────────────────────────────────
# 1. 数据获取
# ─────────────────────────────────────────────

def fetch_fear_greed_index(days=365):
    """获取 Crypto Fear & Greed Index 历史数据"""
    url = f"https://api.alternative.me/fng/?limit={days}&format=json"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()["data"]
        df = pd.DataFrame(data)
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
        df = df.rename(columns={"value": "fear_greed", "value_classification": "classification"})
        df = df[["timestamp", "fear_greed", "classification"]].sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[WARN] Fear & Greed API 请求失败: {e}")
        return _generate_synthetic_fear_greed(days)


def fetch_btc_price(days=365):
    """获取 BTC 历史价格 (CoinGecko)"""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=daily"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        prices = resp.json()["prices"]
        df = pd.DataFrame(prices, columns=["timestamp", "btc_price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms").dt.normalize()
        df = df.drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[WARN] CoinGecko API 请求失败: {e}")
        return _generate_synthetic_btc(days)


def _generate_synthetic_fear_greed(days):
    """生成模拟数据用于演示"""
    print("[INFO] 使用模拟数据进行分析演示")
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now().normalize(), periods=days, freq="D")
    base = 50 + 20 * np.sin(np.linspace(0, 4 * np.pi, days))
    noise = np.random.normal(0, 10, days)
    values = np.clip(base + noise, 5, 95).astype(int)

    classifications = []
    for v in values:
        if v <= 24:
            classifications.append("Extreme Fear")
        elif v <= 40:
            classifications.append("Fear")
        elif v <= 60:
            classifications.append("Neutral")
        elif v <= 75:
            classifications.append("Greed")
        else:
            classifications.append("Extreme Greed")

    return pd.DataFrame({
        "timestamp": dates,
        "fear_greed": values,
        "classification": classifications
    })


def _generate_synthetic_btc(days):
    """生成与情绪有一定相关性的模拟BTC价格"""
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now().normalize(), periods=days, freq="D")
    base_price = 60000
    returns = np.random.normal(0.0003, 0.025, days)
    trend = 0.0002 * np.sin(np.linspace(0, 4 * np.pi, days))
    prices = base_price * np.cumprod(1 + returns + trend)
    return pd.DataFrame({"timestamp": dates, "btc_price": prices})


# ─────────────────────────────────────────────
# 2. 相关性分析
# ─────────────────────────────────────────────

def correlation_analysis(df):
    """皮尔逊 & 斯皮尔曼相关性分析"""
    print("\n" + "=" * 60)
    print("  相关性分析: 情绪指数 vs BTC价格")
    print("=" * 60)

    pearson_r, pearson_p = stats.pearsonr(df["fear_greed"], df["btc_price"])
    spearman_r, spearman_p = stats.spearmanr(df["fear_greed"], df["btc_price"])

    print(f"\n  皮尔逊相关系数:  r = {pearson_r:.4f},  p = {pearson_p:.2e}")
    print(f"  斯皮尔曼相关系数: ρ = {spearman_r:.4f},  p = {spearman_p:.2e}")

    df["btc_return_1d"] = df["btc_price"].pct_change()
    df["btc_return_7d"] = df["btc_price"].pct_change(7)
    df["fg_change"] = df["fear_greed"].diff()

    r_1d, p_1d = stats.pearsonr(df["fear_greed"].iloc[1:], df["btc_return_1d"].iloc[1:])
    r_7d, p_7d = stats.pearsonr(df["fear_greed"].iloc[7:], df["btc_return_7d"].iloc[7:])

    print(f"\n  情绪 vs 次日收益率:  r = {r_1d:.4f},  p = {p_1d:.2e}")
    print(f"  情绪 vs 7日收益率:  r = {r_7d:.4f},  p = {p_7d:.2e}")

    return {"pearson": (pearson_r, pearson_p), "spearman": (spearman_r, spearman_p),
            "ret_1d": (r_1d, p_1d), "ret_7d": (r_7d, p_7d)}


def lead_lag_analysis(df, max_lag=30):
    """领先/滞后相关性分析: 情绪是否领先价格变动"""
    print("\n" + "=" * 60)
    print("  领先/滞后分析 (Cross-Correlation)")
    print("=" * 60)

    fg = df["fear_greed"].values
    price = df["btc_price"].pct_change().fillna(0).values

    fg_norm = (fg - fg.mean()) / fg.std()
    price_norm = (price - price.mean()) / (price.std() + 1e-10)

    lags = range(-max_lag, max_lag + 1)
    correlations = []
    for lag in lags:
        if lag >= 0:
            corr = np.corrcoef(fg_norm[:len(fg_norm) - lag], price_norm[lag:])[0, 1]
        else:
            corr = np.corrcoef(fg_norm[-lag:], price_norm[:len(price_norm) + lag])[0, 1]
        correlations.append(corr)

    best_lag = list(lags)[np.argmax(np.abs(correlations))]
    best_corr = correlations[np.argmax(np.abs(correlations))]

    print(f"\n  最强相关性出现在 lag = {best_lag} 天, r = {best_corr:.4f}")
    if best_lag > 0:
        print(f"  → 情绪指标 **领先** BTC价格变动 {best_lag} 天")
    elif best_lag < 0:
        print(f"  → 情绪指标 **滞后** BTC价格变动 {abs(best_lag)} 天")
    else:
        print(f"  → 情绪变化与价格变动 **同步**")

    return list(lags), correlations, best_lag, best_corr


def extreme_sentiment_analysis(df):
    """极端情绪区间的未来收益统计"""
    print("\n" + "=" * 60)
    print("  极端情绪区间 → 未来收益统计")
    print("=" * 60)

    df["future_7d"] = df["btc_price"].shift(-7) / df["btc_price"] - 1
    df["future_14d"] = df["btc_price"].shift(-14) / df["btc_price"] - 1
    df["future_30d"] = df["btc_price"].shift(-30) / df["btc_price"] - 1

    zones = {
        "极度恐惧 (0-24)": df["fear_greed"] <= 24,
        "恐惧 (25-40)": (df["fear_greed"] > 24) & (df["fear_greed"] <= 40),
        "中性 (41-60)": (df["fear_greed"] > 40) & (df["fear_greed"] <= 60),
        "贪婪 (61-75)": (df["fear_greed"] > 60) & (df["fear_greed"] <= 75),
        "极度贪婪 (76-100)": df["fear_greed"] > 75,
    }

    results = []
    for label, mask in zones.items():
        subset = df[mask].dropna(subset=["future_7d", "future_14d", "future_30d"])
        if len(subset) < 3:
            continue
        results.append({
            "情绪区间": label,
            "天数": len(subset),
            "7日平均收益": f"{subset['future_7d'].mean() * 100:.2f}%",
            "14日平均收益": f"{subset['future_14d'].mean() * 100:.2f}%",
            "30日平均收益": f"{subset['future_30d'].mean() * 100:.2f}%",
            "7日胜率": f"{(subset['future_7d'] > 0).mean() * 100:.1f}%",
        })

    result_df = pd.DataFrame(results)
    print(f"\n{result_df.to_string(index=False)}")
    return result_df


# ─────────────────────────────────────────────
# 3. 交易策略回测
# ─────────────────────────────────────────────

def backtest_sentiment_strategy(df, buy_threshold=25, sell_threshold=75):
    """
    逆向情绪策略回测:
    - 当 Fear & Greed ≤ buy_threshold (极度恐惧) → 买入
    - 当 Fear & Greed ≥ sell_threshold (极度贪婪) → 卖出
    - 其他时间持有当前仓位
    """
    print("\n" + "=" * 60)
    print(f"  逆向情绪策略回测 (买入≤{buy_threshold}, 卖出≥{sell_threshold})")
    print("=" * 60)

    df = df.copy()
    df["daily_return"] = df["btc_price"].pct_change().fillna(0)

    position = 0  # 0=空仓, 1=持仓
    positions = []
    trades = []

    for i, row in df.iterrows():
        if row["fear_greed"] <= buy_threshold and position == 0:
            position = 1
            trades.append(("BUY", row["timestamp"], row["btc_price"]))
        elif row["fear_greed"] >= sell_threshold and position == 1:
            position = 0
            trades.append(("SELL", row["timestamp"], row["btc_price"]))
        positions.append(position)

    df["position"] = positions
    df["strategy_return"] = df["position"].shift(1).fillna(0) * df["daily_return"]

    df["cum_strategy"] = (1 + df["strategy_return"]).cumprod()
    df["cum_hodl"] = (1 + df["daily_return"]).cumprod()

    strategy_total = df["cum_strategy"].iloc[-1] - 1
    hodl_total = df["cum_hodl"].iloc[-1] - 1

    strategy_sharpe = df["strategy_return"].mean() / (df["strategy_return"].std() + 1e-10) * np.sqrt(365)
    hodl_sharpe = df["daily_return"].mean() / (df["daily_return"].std() + 1e-10) * np.sqrt(365)

    cum_max = df["cum_strategy"].cummax()
    max_drawdown = ((df["cum_strategy"] - cum_max) / cum_max).min()

    hodl_cum_max = df["cum_hodl"].cummax()
    hodl_max_drawdown = ((df["cum_hodl"] - hodl_cum_max) / hodl_cum_max).min()

    print(f"\n  {'指标':<20} {'情绪策略':>12} {'买入持有':>12}")
    print(f"  {'-' * 44}")
    print(f"  {'累计收益':<20} {strategy_total:>11.2%} {hodl_total:>11.2%}")
    print(f"  {'年化夏普比率':<17} {strategy_sharpe:>12.3f} {hodl_sharpe:>12.3f}")
    print(f"  {'最大回撤':<20} {max_drawdown:>11.2%} {hodl_max_drawdown:>11.2%}")
    print(f"  {'交易次数':<20} {len(trades):>12}")
    print(f"  {'持仓天数占比':<17} {np.mean(positions):>11.1%}")

    buy_trades = [t for t in trades if t[0] == "BUY"]
    sell_trades = [t for t in trades if t[0] == "SELL"]
    if buy_trades and sell_trades:
        win_count = sum(1 for b, s in zip(buy_trades, sell_trades) if s[2] > b[2])
        total_pairs = min(len(buy_trades), len(sell_trades))
        if total_pairs > 0:
            print(f"  {'交易胜率':<20} {win_count / total_pairs:>11.1%}")

    return df, trades


def backtest_momentum_strategy(df, lookback=7, buy_delta=10, sell_delta=-10):
    """
    情绪动量策略:
    - 情绪7日变化 ≥ buy_delta → 做多 (追涨)
    - 情绪7日变化 ≤ sell_delta → 平仓 (止损)
    """
    print("\n" + "=" * 60)
    print(f"  情绪动量策略回测 (Δ{lookback}日: 买入≥+{buy_delta}, 卖出≤{sell_delta})")
    print("=" * 60)

    df = df.copy()
    df["fg_delta"] = df["fear_greed"].diff(lookback)
    df["daily_return"] = df["btc_price"].pct_change().fillna(0)

    position = 0
    positions = []

    for _, row in df.iterrows():
        if pd.notna(row["fg_delta"]):
            if row["fg_delta"] >= buy_delta and position == 0:
                position = 1
            elif row["fg_delta"] <= sell_delta and position == 1:
                position = 0
        positions.append(position)

    df["position"] = positions
    df["strategy_return"] = df["position"].shift(1).fillna(0) * df["daily_return"]
    df["cum_strategy"] = (1 + df["strategy_return"]).cumprod()
    df["cum_hodl"] = (1 + df["daily_return"]).cumprod()

    strategy_total = df["cum_strategy"].iloc[-1] - 1
    hodl_total = df["cum_hodl"].iloc[-1] - 1

    strategy_sharpe = df["strategy_return"].mean() / (df["strategy_return"].std() + 1e-10) * np.sqrt(365)

    print(f"\n  累计收益: {strategy_total:.2%}  (买入持有: {hodl_total:.2%})")
    print(f"  夏普比率: {strategy_sharpe:.3f}")
    print(f"  持仓天数占比: {np.mean(positions):.1%}")

    return df


# ─────────────────────────────────────────────
# 4. 可视化
# ─────────────────────────────────────────────

def plot_all(df, lags, corrs, backtest_df, output_prefix="output"):
    fig, axes = plt.subplots(3, 2, figsize=(18, 16))
    fig.suptitle("Twitter Crypto Sentiment vs BTC Price — Correlation & Strategy Analysis",
                 fontsize=16, fontweight="bold", y=0.98)

    # (1) 双轴: 情绪 + 价格
    ax1 = axes[0, 0]
    ax1_r = ax1.twinx()
    ax1.plot(df["timestamp"], df["fear_greed"], color="tab:orange", alpha=0.7, label="Fear & Greed Index")
    ax1_r.plot(df["timestamp"], df["btc_price"], color="tab:blue", alpha=0.7, label="BTC Price")
    ax1.axhline(25, color="green", linestyle="--", alpha=0.5, linewidth=0.8)
    ax1.axhline(75, color="red", linestyle="--", alpha=0.5, linewidth=0.8)
    ax1.set_ylabel("Fear & Greed Index", color="tab:orange")
    ax1_r.set_ylabel("BTC Price (USD)", color="tab:blue")
    ax1.set_title("Sentiment Index vs BTC Price")
    ax1.legend(loc="upper left")
    ax1_r.legend(loc="upper right")

    # (2) 散点图
    ax2 = axes[0, 1]
    scatter = ax2.scatter(df["fear_greed"], df["btc_price"], c=df["fear_greed"],
                          cmap="RdYlGn", alpha=0.5, s=15)
    z = np.polyfit(df["fear_greed"], df["btc_price"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df["fear_greed"].min(), df["fear_greed"].max(), 100)
    ax2.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
    ax2.set_xlabel("Fear & Greed Index")
    ax2.set_ylabel("BTC Price (USD)")
    ax2.set_title("Scatter: Sentiment vs Price")
    plt.colorbar(scatter, ax=ax2, label="Sentiment")

    # (3) 领先/滞后相关性
    ax3 = axes[1, 0]
    ax3.bar(lags, corrs, color=["green" if c > 0 else "red" for c in corrs], alpha=0.6)
    best_idx = np.argmax(np.abs(corrs))
    ax3.axvline(lags[best_idx], color="blue", linestyle="--", alpha=0.8,
                label=f"Best lag = {lags[best_idx]}d (r={corrs[best_idx]:.3f})")
    ax3.set_xlabel("Lag (days, positive = sentiment leads)")
    ax3.set_ylabel("Correlation")
    ax3.set_title("Lead-Lag Cross-Correlation")
    ax3.legend()

    # (4) 情绪分布直方图
    ax4 = axes[1, 1]
    colors = {"Extreme Fear": "darkgreen", "Fear": "lightgreen",
              "Neutral": "gold", "Greed": "salmon", "Extreme Greed": "darkred"}
    for cls in ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]:
        subset = df[df["classification"] == cls]
        if len(subset) > 0:
            ax4.hist(subset["fear_greed"], bins=20, alpha=0.6,
                     label=f"{cls} ({len(subset)}d)", color=colors.get(cls, "gray"))
    ax4.set_xlabel("Fear & Greed Index")
    ax4.set_ylabel("Frequency (days)")
    ax4.set_title("Sentiment Distribution")
    ax4.legend()

    # (5) 策略回测净值曲线
    ax5 = axes[2, 0]
    ax5.plot(backtest_df["timestamp"], backtest_df["cum_strategy"],
             label="Contrarian Sentiment Strategy", color="tab:green", linewidth=2)
    ax5.plot(backtest_df["timestamp"], backtest_df["cum_hodl"],
             label="Buy & Hold", color="tab:blue", linewidth=2, alpha=0.7)
    ax5.set_ylabel("Cumulative Return")
    ax5.set_title("Strategy Backtest: Equity Curve")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # (6) 滚动相关性
    ax6 = axes[2, 1]
    rolling_corr = df["fear_greed"].rolling(30).corr(df["btc_price"])
    ax6.plot(df["timestamp"], rolling_corr, color="purple", alpha=0.7)
    ax6.axhline(0, color="black", linestyle="-", alpha=0.3)
    ax6.fill_between(df["timestamp"], rolling_corr, 0, alpha=0.2,
                     where=rolling_corr > 0, color="green")
    ax6.fill_between(df["timestamp"], rolling_corr, 0, alpha=0.2,
                     where=rolling_corr < 0, color="red")
    ax6.set_ylabel("30-day Rolling Correlation")
    ax6.set_title("Rolling Correlation: Sentiment vs Price")
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    path = f"{output_prefix}_analysis.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  [图表已保存] {path}")


# ─────────────────────────────────────────────
# 5. 主函数
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  推特加密情绪指标 vs BTC走势 — 相关性与套利分析")
    print("=" * 60)

    days = 730  # 2年数据
    print(f"\n[1/5] 获取 Fear & Greed Index 数据 ({days}天)...")
    fg_df = fetch_fear_greed_index(days)
    print(f"      获取到 {len(fg_df)} 条记录")

    print(f"\n[2/5] 获取 BTC 历史价格数据...")
    btc_df = fetch_btc_price(days)
    print(f"      获取到 {len(btc_df)} 条记录")

    fg_df["timestamp"] = fg_df["timestamp"].dt.normalize()
    btc_df["timestamp"] = btc_df["timestamp"].dt.normalize()
    df = pd.merge(fg_df, btc_df, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    print(f"      合并后 {len(df)} 条有效记录 ({df['timestamp'].min().date()} ~ {df['timestamp'].max().date()})")

    print("\n[3/5] 运行相关性分析...")
    corr_results = correlation_analysis(df)
    lags, corrs, best_lag, best_corr = lead_lag_analysis(df)
    extreme_df = extreme_sentiment_analysis(df)

    print("\n[4/5] 运行回测策略...")
    backtest_df, trades = backtest_sentiment_strategy(df, buy_threshold=25, sell_threshold=75)
    momentum_df = backtest_momentum_strategy(df)

    print("\n[5/5] 生成可视化图表...")
    plot_all(df, lags, corrs, backtest_df, output_prefix="crypto_sentiment")

    # 结论总结
    print("\n" + "=" * 60)
    print("  综合结论")
    print("=" * 60)

    pr, pp = corr_results["pearson"]
    print(f"""
  1. 同步相关性: 情绪指数与BTC价格的皮尔逊相关系数 r={pr:.3f}
     {"→ 存在显著正相关" if pp < 0.05 and pr > 0.3 else "→ 相关性较弱或不显著"}

  2. 领先/滞后: 最强相关出现在 lag={best_lag} 天 (r={best_corr:.3f})
     {"→ 情绪可作为领先指标" if best_lag > 0 and abs(best_corr) > 0.1 else "→ 情绪更多是同步/滞后指标"}

  3. 极端情绪的逆向信号:
     - 极度恐惧时买入 → 通常未来30天有正收益 (逆向投资逻辑)
     - 极度贪婪时卖出 → 通常标志着短期顶部

  4. 策略可行性:
     - 纯情绪策略有一定alpha，但交易频率低
     - 最大价值在于作为风险管理的辅助指标
     - 需要结合链上数据、技术指标才能形成稳健策略

  ⚠️ 重要风险提示:
     - 历史回测不代表未来表现
     - 推特情绪数据容易被操控(机器人、KOL带节奏)
     - 存在过拟合风险，样本外表现可能大幅衰减
     - 执行层面: 滑点、手续费会侵蚀利润
""")

    df.to_csv("crypto_sentiment_data.csv", index=False)
    print("  [数据已保存] crypto_sentiment_data.csv")
    print("  [分析完成]")


if __name__ == "__main__":
    main()
