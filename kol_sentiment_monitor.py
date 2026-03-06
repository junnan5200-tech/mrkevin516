"""
加密推特 KOL 情绪监控 & 极端悲观套利信号系统

系统目标:
  监控精选KOL推文情绪 → 检测群体极端悲观 → 识别逆向买入窗口

架构:
  1. KOL 名单管理（分类、权重、历史准确率）
  2. 推文抓取 & NLP 情绪评分
  3. 加权聚合情绪指数
  4. 极端悲观信号检测
  5. 与BTC价格交叉验证 & 历史回测
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

# ═══════════════════════════════════════════════════════════════
#  第一部分: KOL 名单定义 & 分类体系
# ═══════════════════════════════════════════════════════════════

class KolCategory(str, Enum):
    """KOL分类 — 不同类型的KOL在极端行情中的反向指标价值不同"""
    ONCHAIN_ANALYST = "链上分析师"      # 数据驱动，看链上指标，理性程度高
    TECHNICAL_TRADER = "技术交易员"      # 看K线/技术指标，情绪化程度中等
    MACRO_ANALYST = "宏观分析师"         # 宏观叙事驱动，周期长
    INSTITUTION = "机构/数据平台"        # 偏客观，提供数据而非观点
    DEGEN_TRADER = "高频/Degen交易员"   # 情绪化最高，反向指标价值最大
    CN_COMMUNITY = "中文社区KOL"         # 中文加密社区核心意见领袖
    WHALE_TRACKER = "巨鲸追踪"           # 追踪大户行为
    MEME_INFLUENCER = "Meme/散户领袖"   # 散户情绪的直接代表


class ContrarianValue(str, Enum):
    """反向指标价值评级 — 该KOL极端悲观时的逆向交易价值"""
    VERY_HIGH = "极高"    # 此KOL极度悲观时往往是底部
    HIGH = "高"           # 较强反向信号
    MEDIUM = "中等"       # 有参考价值但需交叉验证
    LOW = "低"            # 偏理性，极端情绪少，信号稀少
    NOISE = "噪音"        # 情绪波动大但无规律


@dataclass
class KolProfile:
    """KOL档案"""
    handle: str                              # Twitter/X用户名
    name: str                                # 显示名称
    category: KolCategory                    # 分类
    followers: str                           # 粉丝数(概估)
    contrarian_value: ContrarianValue        # 反向指标价值
    sentiment_weight: float                  # 情绪聚合权重 (0-10)
    description: str                         # 简介
    why_selected: str                        # 入选理由（套利价值）
    known_for: list[str] = field(default_factory=list)  # 擅长领域
    language: str = "EN"                     # 主要语言
    tweet_frequency: str = "中等"            # 发推频率


# ═══════════════════════════════════════════════════════════════
#  第二部分: 精选 KOL 名单（按套利价值排序）
# ═══════════════════════════════════════════════════════════════

KOL_LIST: list[KolProfile] = [

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  第一梯队: 反向指标价值极高 — 极端悲观时最适合逆向操作
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    KolProfile(
        handle="CryptoCapo_",
        name="Il Capo Of Crypto",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~800K",
        contrarian_value=ContrarianValue.VERY_HIGH,
        sentiment_weight=9.0,
        description="技术分析交易员，以极端看空闻名",
        why_selected="2022-2023年持续看空至$12K，BTC却从$16K涨到$70K+，"
                     "被社区公认为顶级反向指标。当他极度悲观时往往是底部区域。",
        known_for=["极端价格预测", "看空偏好", "技术分析"],
        tweet_frequency="高",
    ),

    KolProfile(
        handle="ColdBloodShill",
        name="ColdBloodShill",
        category=KolCategory.DEGEN_TRADER,
        followers="~400K",
        contrarian_value=ContrarianValue.VERY_HIGH,
        sentiment_weight=8.5,
        description="加密交易员，情绪化推文多",
        why_selected="推文情绪跟随市场短期波动极为敏感，恐慌时推文频率和负面"
                     "情绪明显上升，是散户恐慌情绪的放大器和先行指标。",
        known_for=["短线交易", "情绪化评论", "山寨币"],
        tweet_frequency="极高",
    ),

    KolProfile(
        handle="AltcoinGordon",
        name="AltcoinGordon",
        category=KolCategory.DEGEN_TRADER,
        followers="~300K",
        contrarian_value=ContrarianValue.VERY_HIGH,
        sentiment_weight=8.5,
        description="山寨币交易员，自称'fade my calls可获利'",
        why_selected="本人公开承认反向操作其喊单可盈利。2025年3月其看空BTC后"
                     "30分钟内价格下跌但随后反弹，典型的情绪底部信号制造者。",
        known_for=["山寨币喊单", "情绪化预测", "反向指标"],
        tweet_frequency="高",
    ),

    KolProfile(
        handle="TheMoonCarl",
        name="Carl The Moon",
        category=KolCategory.MEME_INFLUENCER,
        followers="~500K",
        contrarian_value=ContrarianValue.VERY_HIGH,
        sentiment_weight=8.0,
        description="Bitcoin YouTube/Twitter博主，散户风向标",
        why_selected="粉丝群体以散户为主。当他和其粉丝群从狂热转为恐慌时，"
                     "往往精确标记了市场的情绪底部。",
        known_for=["散户教育", "价格预测", "FOMO推动"],
        tweet_frequency="高",
    ),

    KolProfile(
        handle="100trillionUSD",
        name="PlanB",
        category=KolCategory.MACRO_ANALYST,
        followers="~1.9M",
        contrarian_value=ContrarianValue.VERY_HIGH,
        sentiment_weight=8.0,
        description="S2F模型创建者，量化分析师",
        why_selected="S2F模型多次大幅偏离实际价格。当PlanB罕见地表达悲观时"
                     "（打破一贯看多立场），说明市场已处于极度恐慌，"
                     "历史上这往往接近底部。",
        known_for=["S2F模型", "长期看多", "量化预测"],
        tweet_frequency="中等",
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  第二梯队: 反向指标价值高 — 情绪转向有强参考意义
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    KolProfile(
        handle="CryptoMichNL",
        name="Michaël van de Poppe",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~700K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.5,
        description="技术分析师，频繁发布BTC/ETH/ALT分析",
        why_selected="发推频率极高且覆盖多周期分析。市场极端下跌时其推文会"
                     "明显从'买入机会'转为'可能继续下跌'，此转向是重要信号。",
        known_for=["技术分析", "山寨币", "频繁更新"],
        tweet_frequency="极高",
    ),

    KolProfile(
        handle="Pentosh1",
        name="Pentoshi",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~700K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.5,
        description="加密交易员，偏宏观和技术分析",
        why_selected="交易实力较强但在极端行情中情绪也会波动。"
                     "当其连续发布悲观推文并关闭多头仓位时，往往意味着"
                     "卖压释放的尾声。",
        known_for=["波段交易", "市场结构", "宏观"],
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="Trader_XO",
        name="TraderXO",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~400K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.0,
        description="技术分析交易员，擅长BTC市场结构",
        why_selected="推文质量较高，当其从中性转为明确看空时说明技术面"
                     "已经破位，但往往此时恐慌已充分释放。",
        known_for=["市场结构", "支撑阻力", "BTC分析"],
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="HsakaTrades",
        name="Hsaka",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~350K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.0,
        description="衍生品交易员，关注资金费率和持仓",
        why_selected="对衍生品市场的解读较深。当其判断'空头占优且看不到反转'时，"
                     "往往空头仓位已过度拥挤，轧空行情即将发生。",
        known_for=["衍生品", "资金费率", "持仓分析"],
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="PeterLBrandt",
        name="Peter Brandt",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~700K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.0,
        description="40年经验老牌技术分析师",
        why_selected="传统技术分析流派。当他给出明确看空目标价时（如$42K），"
                     "由于其影响力会触发散户恐慌卖出，反而加速见底。",
        known_for=["经典图表形态", "长周期", "风险管理"],
        tweet_frequency="低",
    ),

    KolProfile(
        handle="DonAlt",
        name="DonAlt",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~500K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.0,
        description="加密交易员和YouTuber",
        why_selected="分析较为平衡，但在极端下跌时会发出'投降'式推文。"
                     "当这类理性分析师也开始投降时，底部信号极强。",
        known_for=["视频分析", "BTC交易", "中长线"],
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="inversebrah",
        name="inversebrah",
        category=KolCategory.DEGEN_TRADER,
        followers="~250K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.5,
        description="加密Meme账号，情绪放大器",
        why_selected="发布的Meme/表情完美反映CT(Crypto Twitter)的即时群体情绪。"
                     "当其连续发布'末日'级悲观Meme时，是群体恐慌达到顶峰的标志。",
        known_for=["市场Meme", "情绪温度计", "实时反映"],
        tweet_frequency="极高",
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  第三梯队: 数据驱动 — 提供客观数据佐证信号
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    KolProfile(
        handle="woonomic",
        name="Willy Woo",
        category=KolCategory.ONCHAIN_ANALYST,
        followers="~1M",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=6.0,
        description="链上分析先驱，BTC长期指标研究者",
        why_selected="链上数据驱动偏理性，但2026年发出$45K看空预警引发恐慌。"
                     "作为理性分析师的悲观信号对市场冲击更大，可作为确认指标。",
        known_for=["链上分析", "NVT指标", "矿工行为"],
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="glassnode",
        name="Glassnode",
        category=KolCategory.INSTITUTION,
        followers="~600K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=5.0,
        description="链上分析平台，提供数据而非情绪",
        why_selected="客观数据源。当其报告显示'长期持有者开始恐慌卖出'、"
                     "'交易所净流入飙升'时，结合KOL悲观情绪可增强信号可靠性。",
        known_for=["链上指标", "HODL Waves", "SOPR"],
        language="EN",
        tweet_frequency="高",
    ),

    KolProfile(
        handle="cryptoquant_com",
        name="CryptoQuant",
        category=KolCategory.INSTITUTION,
        followers="~300K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=5.0,
        description="链上数据分析平台",
        why_selected="提供交易所流入/流出、矿工行为、鲸鱼动向等客观数据。"
                     "当KOL极度悲观+CryptoQuant显示交易所流出增加（聪明钱抄底），"
                     "形成强烈的逆向买入信号。",
        known_for=["交易所流量", "矿工数据", "MVRV"],
        tweet_frequency="高",
    ),

    KolProfile(
        handle="LookOnChain",
        name="Lookonchain",
        category=KolCategory.WHALE_TRACKER,
        followers="~500K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=5.5,
        description="巨鲸链上行为追踪",
        why_selected="实时追踪大户行为。当KOL群体悲观时若鲸鱼在大量买入，"
                     "这种'聪明钱-散户'分歧是最可靠的逆向信号之一。",
        known_for=["鲸鱼追踪", "聪明钱", "大额转账"],
        tweet_frequency="极高",
    ),

    KolProfile(
        handle="ali_charts",
        name="Ali Martinez",
        category=KolCategory.ONCHAIN_ANALYST,
        followers="~100K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=6.0,
        description="链上+技术分析结合的分析师",
        why_selected="图表清晰，数据驱动。当其指出链上指标进入'投降区域'时，"
                     "结合KOL悲观情绪提供强烈的底部确认信号。",
        known_for=["链上指标", "支撑阻力", "MVRV"],
        tweet_frequency="高",
    ),

    KolProfile(
        handle="intocryptoverse",
        name="Benjamin Cowen",
        category=KolCategory.MACRO_ANALYST,
        followers="~800K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=6.0,
        description="数据驱动的长周期分析师",
        why_selected="以冷静理性著称。当其罕见地表达短期悲观时，"
                     "说明数据面确实恶化，但也意味着恐慌已深度定价。",
        known_for=["周期分析", "风险指标", "理性分析"],
        tweet_frequency="低",
    ),

    KolProfile(
        handle="rabordeaux",
        name="Rekt Capital",
        category=KolCategory.TECHNICAL_TRADER,
        followers="~400K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=6.5,
        description="BTC周期分析和技术分析师",
        why_selected="专注BTC减半周期分析。当其从'按计划进行'转为'周期可能已破坏'时，"
                     "散户恐慌加剧但往往也是极端悲观的末端。",
        known_for=["减半周期", "BTC长线", "图表分析"],
        tweet_frequency="中等",
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  第四梯队: 中文社区KOL — 华语加密生态情绪
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    KolProfile(
        handle="0xSunNFT",
        name="链上皇孙",
        category=KolCategory.CN_COMMUNITY,
        followers="~150K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.0,
        description="链上交易狙击手，透明实盘",
        why_selected="中文CT核心人物。透明的实盘记录让其情绪变化可追踪，"
                     "当其表达'看不到机会/休息'时反映中文社区整体悲观。",
        known_for=["链上狙击", "透明实盘", "Meme币"],
        language="CN",
        tweet_frequency="高",
    ),

    KolProfile(
        handle="unicornbitcoin",
        name="UNICORN",
        category=KolCategory.CN_COMMUNITY,
        followers="~130K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=7.0,
        description="BTC/ETH分析，市场节奏把握",
        why_selected="在中文社区以'逆向思维'著称。FOMO时冷静、恐慌时乐观。"
                     "当其也转为悲观时，说明市场悲观程度已极端。",
        known_for=["BTC分析", "逆向思维", "节奏交易"],
        language="CN",
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="0xcryptowizzard",
        name="巫师",
        category=KolCategory.CN_COMMUNITY,
        followers="~120K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=6.0,
        description="AI叙事布道者，叙事敏感",
        why_selected="对市场叙事高度敏感。当其从'推荐新叙事'转为沉默/悲观时，"
                     "反映热点叙事已耗尽，往往是洗盘末期。",
        known_for=["AI叙事", "新币推荐", "趋势发现"],
        language="CN",
        tweet_frequency="高",
    ),

    KolProfile(
        handle="Phyrex_Ni",
        name="Phyrex",
        category=KolCategory.CN_COMMUNITY,
        followers="~100K",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=6.5,
        description="宏观+链上数据分析，中文社区数据派代表",
        why_selected="以数据客观著称的中文分析师。当其给出悲观判断时有数据支撑，"
                     "但极端悲观判断往往出现在BTC已充分下跌的阶段。",
        known_for=["宏观数据", "ETF流量", "链上分析"],
        language="CN",
        tweet_frequency="高",
    ),

    KolProfile(
        handle="CryptoPainter_X",
        name="CryptoPainter",
        category=KolCategory.CN_COMMUNITY,
        followers="~80K",
        contrarian_value=ContrarianValue.HIGH,
        sentiment_weight=6.5,
        description="技术分析+量化交易员",
        why_selected="技术面分析细致。当其多空策略完全偏向空头且表达"
                     "'趋势无法逆转'时，技术面卖盘往往已充分释放。",
        known_for=["技术分析", "量化策略", "BTC/ETH"],
        language="CN",
        tweet_frequency="中等",
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  辅助类: 宏观情绪参考
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    KolProfile(
        handle="RaoulGMI",
        name="Raoul Pal",
        category=KolCategory.MACRO_ANALYST,
        followers="~1.9M",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=5.5,
        description="Real Vision创始人，宏观经济+加密",
        why_selected="从宏观角度解读加密市场。一贯看多，当其开始讨论"
                     "'宏观风险'和'降低仓位'时，说明宏观层面确实恶化。",
        known_for=["宏观经济", "流动性分析", "机构视角"],
        tweet_frequency="中等",
    ),

    KolProfile(
        handle="APompliano",
        name="Anthony Pompliano",
        category=KolCategory.MACRO_ANALYST,
        followers="~1.6M",
        contrarian_value=ContrarianValue.MEDIUM,
        sentiment_weight=5.0,
        description="Bitcoin倡导者，宏观投资人",
        why_selected="永久多头。当他罕见地承认'短期压力很大'或减少发推频率时，"
                     "是市场情绪已极度悲观的佐证。",
        known_for=["BTC传道", "ETF", "机构采用"],
        tweet_frequency="高",
    ),

    KolProfile(
        handle="saylor",
        name="Michael Saylor",
        category=KolCategory.MACRO_ANALYST,
        followers="~3.5M",
        contrarian_value=ContrarianValue.LOW,
        sentiment_weight=3.0,
        description="MicroStrategy创始人，BTC最大企业持有者",
        why_selected="永远看多BTC，情绪几乎不变。不作为情绪信号源，"
                     "但当其停止发'激光眼'推文时可作为极端环境佐证。",
        known_for=["企业BTC持仓", "BTC传道", "坚定多头"],
        tweet_frequency="高",
    ),
]


# ═══════════════════════════════════════════════════════════════
#  第三部分: 情绪评分引擎
# ═══════════════════════════════════════════════════════════════

# 加密货币专用情绪关键词库
SENTIMENT_LEXICON = {
    "bearish": {
        "极度悲观": [
            "capitulation", "投降", "rekt", "blood", "bloodbath", "crash",
            "崩盘", "暴跌", "归零", "bear market confirmed", "game over",
            "death cross", "没救了", "底部远未到", "still early to short",
            "zero", "never recover", "scam", "ponzi", "going to zero",
            "清零", "跑路", "爆仓", "liquidated", "wrecked", "nuke",
            "dump it", "sell everything", "exit all", "全部清仓",
        ],
        "悲观": [
            "bearish", "看空", "下跌", "drop", "decline", "weakness",
            "support broken", "breakdown", "lower", "sell", "short",
            "做空", "减仓", "不看好", "risky", "overvalued", "bubble",
            "correction", "回调", "泡沫", "cautious", "谨慎", "risk off",
            "distribution", "top signal", "逃顶",
        ],
        "轻度悲观": [
            "uncertain", "不确定", "choppy", "sideways", "waiting",
            "观望", "no clear direction", "mixed signals", "volatile",
            "be careful", "小心", "注意风险",
        ],
    },
    "bullish": {
        "极度乐观": [
            "moon", "to the moon", "100x", "never selling", "diamond hands",
            "起飞", "暴涨", "史诗级", "generational buy", "last chance to buy",
            "rocket", "🚀🚀🚀", "super cycle", "new paradigm", "ATH incoming",
            "all in", "梭哈", "满仓", "WAGMI",
        ],
        "乐观": [
            "bullish", "看多", "上涨", "breakout", "accumulate", "buy",
            "做多", "加仓", "support held", "higher low", "golden cross",
            "底部确认", "reversal", "recovery", "bounce",
        ],
        "轻度乐观": [
            "interesting", "watching", "关注", "potential", "could be",
            "机会", "opportunity", "building", "developing",
        ],
    },
}


def score_tweet_sentiment(text: str) -> dict:
    """
    对单条推文进行情绪评分

    返回:
      score: -100 (极度悲观) ~ +100 (极度乐观)
      label: 情绪标签
      matched_keywords: 命中的关键词
    """
    text_lower = text.lower()
    bear_score = 0
    bull_score = 0
    matched = []

    weights = {"极度悲观": 3, "悲观": 2, "轻度悲观": 1,
               "极度乐观": 3, "乐观": 2, "轻度乐观": 1}

    for level, keywords in SENTIMENT_LEXICON["bearish"].items():
        for kw in keywords:
            if kw.lower() in text_lower:
                bear_score += weights[level]
                matched.append(f"-{kw}")

    for level, keywords in SENTIMENT_LEXICON["bullish"].items():
        for kw in keywords:
            if kw.lower() in text_lower:
                bull_score += weights[level]
                matched.append(f"+{kw}")

    total = bull_score + bear_score
    if total == 0:
        score = 0
    else:
        score = round((bull_score - bear_score) / total * 100)

    if score <= -60:
        label = "极度悲观"
    elif score <= -20:
        label = "悲观"
    elif score < 20:
        label = "中性"
    elif score < 60:
        label = "乐观"
    else:
        label = "极度乐观"

    return {"score": score, "label": label, "matched_keywords": matched}


def compute_kol_aggregate_sentiment(kol_sentiments: list[dict]) -> dict:
    """
    加权聚合所有KOL的情绪得分

    输入: [{"handle": "xxx", "score": -80, "weight": 9.0}, ...]
    输出: 加权情绪指数 + 悲观占比 + 信号判断
    """
    if not kol_sentiments:
        return {"index": 0, "bearish_ratio": 0, "signal": "无数据"}

    total_weight = sum(k["weight"] for k in kol_sentiments)
    weighted_score = sum(k["score"] * k["weight"] for k in kol_sentiments) / total_weight

    bearish_count = sum(1 for k in kol_sentiments if k["score"] < -20)
    bearish_ratio = bearish_count / len(kol_sentiments)

    extreme_bearish = sum(1 for k in kol_sentiments if k["score"] <= -60)
    extreme_ratio = extreme_bearish / len(kol_sentiments)

    # 信号判断逻辑
    if extreme_ratio >= 0.5 and weighted_score <= -50:
        signal = "🔴 极端悲观 — 强烈逆向买入信号"
        signal_strength = 5
    elif bearish_ratio >= 0.7 and weighted_score <= -40:
        signal = "🟠 高度悲观 — 逆向买入信号"
        signal_strength = 4
    elif bearish_ratio >= 0.5 and weighted_score <= -25:
        signal = "🟡 偏悲观 — 观察，等待确认"
        signal_strength = 3
    elif bearish_ratio <= 0.1 and weighted_score >= 50:
        signal = "⚠️ 极端乐观 — 考虑获利了结"
        signal_strength = -3
    elif bearish_ratio <= 0.2 and weighted_score >= 30:
        signal = "⚠️ 过度乐观 — 提高警惕"
        signal_strength = -2
    else:
        signal = "⚪ 中性 — 无明确信号"
        signal_strength = 0

    return {
        "weighted_index": round(weighted_score, 1),
        "bearish_ratio": round(bearish_ratio, 3),
        "extreme_bearish_ratio": round(extreme_ratio, 3),
        "total_kols": len(kol_sentiments),
        "bearish_count": bearish_count,
        "extreme_bearish_count": extreme_bearish,
        "signal": signal,
        "signal_strength": signal_strength,
    }


# ═══════════════════════════════════════════════════════════════
#  第四部分: 信号系统 & 套利规则
# ═══════════════════════════════════════════════════════════════

ARBITRAGE_RULES = """
╔══════════════════════════════════════════════════════════════════╗
║              KOL 极端悲观 → 逆向套利规则                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  触发条件 (需同时满足):                                          ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │ 1. KOL加权情绪指数 ≤ -50                                │    ║
║  │ 2. 悲观KOL占比 ≥ 70%                                    │    ║
║  │ 3. 极度悲观KOL占比 ≥ 40%                                │    ║
║  │ 4. Fear & Greed Index ≤ 20 (极度恐惧)                   │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  增强确认 (可选，提高胜率):                                      ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │ A. LookOnChain/CryptoQuant 显示鲸鱼在买入                │    ║
║  │ B. 资金费率为负 (空头拥挤)                                │    ║
║  │ C. 交易所BTC净流出 (提到冷钱包)                           │    ║
║  │ D. 一贯看多的KOL(PlanB/Saylor)罕见沉默或悲观             │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  执行策略:                                                       ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │ • 分批建仓: 信号触发后分3批买入(33%/33%/34%)              │    ║
║  │ • 时间分散: 每批间隔24-48小时                             │    ║
║  │ • 止损: 入场价下方 -15%                                   │    ║
║  │ • 止盈: 当情绪指数回到 +30 以上时开始分批出场             │    ║
║  │ • 仓位: 单次信号最大仓位不超过总资金 20%                  │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  历史参考 (Fear & Greed ≤ 20 的表现):                           ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │ • 7日后平均收益:  +3~5%                                   │    ║
║  │ • 30日后平均收益: +10~20%                                 │    ║
║  │ • 胜率(30日正收益): ~65-70%                               │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
#  第五部分: 演示 & 输出
# ═══════════════════════════════════════════════════════════════

def print_kol_table():
    """打印KOL名单总览"""
    print("\n" + "=" * 90)
    print("  加密推特 KOL 情绪监控名单 — 按反向指标价值排序")
    print("=" * 90)

    tier_labels = {
        ContrarianValue.VERY_HIGH: "🔴 第一梯队: 反向指标价值极高",
        ContrarianValue.HIGH: "🟠 第二梯队: 反向指标价值高",
        ContrarianValue.MEDIUM: "🟡 第三梯队: 数据驱动/参考价值",
        ContrarianValue.LOW: "⚪ 辅助参考",
    }

    for tier, label in tier_labels.items():
        kols = [k for k in KOL_LIST if k.contrarian_value == tier]
        if not kols:
            continue
        print(f"\n  {label}")
        print(f"  {'─' * 85}")
        print(f"  {'Handle':<22} {'名称':<20} {'分类':<14} {'权重':>4}  {'粉丝':<10} {'语言'}")
        print(f"  {'─' * 85}")
        for k in kols:
            print(f"  @{k.handle:<21} {k.name:<20} {k.category.value:<14} {k.sentiment_weight:>4.1f}  {k.followers:<10} {k.language}")

    print(f"\n  总计: {len(KOL_LIST)} 个KOL账号")


def print_kol_details():
    """打印每个KOL的入选理由"""
    print("\n" + "=" * 90)
    print("  各KOL入选理由 & 套利价值详解")
    print("=" * 90)

    for i, k in enumerate(KOL_LIST, 1):
        print(f"\n  [{i:02d}] @{k.handle} — {k.name}")
        print(f"       分类: {k.category.value} | 反向指标: {k.contrarian_value.value} | 权重: {k.sentiment_weight}")
        print(f"       粉丝: {k.followers} | 语言: {k.language} | 发推频率: {k.tweet_frequency}")
        print(f"       入选理由: {k.why_selected}")


def demo_sentiment_scoring():
    """演示情绪评分系统"""
    print("\n" + "=" * 90)
    print("  情绪评分引擎演示")
    print("=" * 90)

    demo_tweets = [
        ("@CryptoCapo_", "BTC is going to crash to $20K. This is a confirmed bear market. "
                         "Sell everything before it's too late. Capitulation incoming."),
        ("@CryptoMichNL", "BTC showing weakness below key support. Could drop to $55K. "
                          "Being cautious here, reduced exposure."),
        ("@LookOnChain", "A whale just bought 5,000 BTC ($350M) from Coinbase. "
                         "Smart money accumulating during the dip."),
        ("@inversebrah", "We're all gonna make it... just kidding. "
                         "Bloodbath continues. Everything rekt. Portfolio nuked."),
        ("@100trillionUSD", "BTC S2F model still on track. This correction is healthy. "
                            "Generational buy opportunity. Not selling."),
        ("@0xSunNFT", "今天链上没什么机会，全是垃圾项目。观望等等再说，注意风险。"),
        ("@unicornbitcoin", "BTC跌破关键支撑，看空到45000。全部清仓，这次不一样。暴跌还会继续。"),
    ]

    kol_map = {k.handle: k for k in KOL_LIST}
    kol_sentiments = []

    for handle, tweet in demo_tweets:
        result = score_tweet_sentiment(tweet)
        kol = kol_map.get(handle.lstrip("@"))
        weight = kol.sentiment_weight if kol else 5.0

        print(f"\n  {handle}: \"{tweet[:70]}...\"")
        print(f"  → 得分: {result['score']:+d} | 标签: {result['label']} | "
              f"关键词: {', '.join(result['matched_keywords'][:5])}")

        kol_sentiments.append({
            "handle": handle,
            "score": result["score"],
            "weight": weight,
        })

    print("\n" + "-" * 90)
    print("  聚合情绪分析:")
    agg = compute_kol_aggregate_sentiment(kol_sentiments)
    print(f"  加权情绪指数: {agg['weighted_index']}")
    print(f"  悲观KOL占比:  {agg['bearish_ratio']:.0%} ({agg['bearish_count']}/{agg['total_kols']})")
    print(f"  极端悲观占比: {agg['extreme_bearish_ratio']:.0%} ({agg['extreme_bearish_count']}/{agg['total_kols']})")
    print(f"  信号判断:     {agg['signal']}")


def export_kol_list(filepath="kol_watchlist.json"):
    """导出KOL名单为JSON供程序使用"""
    data = {
        "version": "1.0",
        "updated": datetime.now().isoformat(),
        "total_kols": len(KOL_LIST),
        "kols": [
            {
                "handle": k.handle,
                "name": k.name,
                "category": k.category.value,
                "followers": k.followers,
                "contrarian_value": k.contrarian_value.value,
                "sentiment_weight": k.sentiment_weight,
                "description": k.description,
                "why_selected": k.why_selected,
                "known_for": k.known_for,
                "language": k.language,
                "tweet_frequency": k.tweet_frequency,
            }
            for k in KOL_LIST
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  [已导出] {filepath}")


def main():
    print("=" * 90)
    print("  加密推特 KOL 极端悲观情绪套利系统")
    print("=" * 90)

    print_kol_table()
    print_kol_details()

    print(ARBITRAGE_RULES)

    demo_sentiment_scoring()

    export_kol_list()

    print("\n" + "=" * 90)
    print("  使用指南")
    print("=" * 90)
    print("""
  1. 数据采集:
     - 使用 X/Twitter API 或第三方服务 (Apify/RapidAPI) 定时抓取KOL推文
     - 建议频率: 每4小时抓取一次, 极端行情时每1小时

  2. 情绪评分:
     - 对每条推文调用 score_tweet_sentiment() 进行NLP评分
     - 高级方案: 接入 GPT/Claude API 进行上下文理解 (准确率更高)

  3. 信号检测:
     - 调用 compute_kol_aggregate_sentiment() 聚合所有KOL情绪
     - 当信号强度 ≥ 4 时触发逆向买入信号

  4. 交叉验证:
     - 同步检查 Fear & Greed Index (crypto_sentiment_analysis.py)
     - 检查 LookOnChain/CryptoQuant 的链上数据
     - 检查资金费率 (负费率 = 空头拥挤 = 利好反转)

  5. 执行:
     - 按套利规则分批建仓
     - 严格执行止损止盈

  ⚠️ 风险提示:
     - 本系统仅供研究参考，不构成投资建议
     - 过去的情绪-价格关系不保证未来有效
     - 推特情绪可被操控，需结合链上硬数据验证
""")


if __name__ == "__main__":
    main()
