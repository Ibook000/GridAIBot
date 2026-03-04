# pyright: reportArgumentType=false, reportGeneralTypeIssues=false
"""
AI 交易分析脚本
技术面 + 消息面 LLM 分析，整合一周行情多空预测
每天定时推送到 Discord
"""
import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

# 加载 webhook 目录下的配置文件
webhook_dir = Path(__file__).parent
load_dotenv(webhook_dir / "config.env")
sys.path.insert(0, str(webhook_dir))
import config

# ==================== 配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Discord Webhook URL
WEBHOOK_URL = config.DISCORD_WEBHOOK_URL

# 交易对配置
SYMBOLS = config.TRADING_SYMBOLS
ANALYSIS_TIME = config.TRADING_ANALYSIS_TIME

# OKX API
OKX_BASE_URL = "https://www.okx.com"

# 数据存储路径（相对于 webhook 目录）
DATA_DIR = Path(__file__).parent / "trading_analysis"
HISTORY_FILE = DATA_DIR / "analysis_history.json"

# ==================== LLM 客户端 ====================
class LLMClient:
    """LLM 客户端封装"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._llm = None
        self._initialized = True

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                base_url=config.LLM_BASE_URL,
                api_key=SecretStr(config.LLM_API_KEY),
                model=config.LLM_MODEL,
                temperature=0.3,
            )
        return self._llm

    def analyze(self, prompt: str) -> str:
        """
        调用 LLM 进行分析

        Args:
            prompt: 分析提示词

        Returns:
            LLM 返回的分析结果
        """
        try:
            print(f"[DEBUG] 调用 LLM 分析: {prompt}")
            response = self.llm.invoke(prompt)
            # 处理不同的返回格式
            if hasattr(response, 'content'):
                return response.content
            # 兼容字典格式
            if isinstance(response, dict):
                if 'content' in response:
                    return response['content']
                # 兼容 OpenAI 格式
                choices = response.get('choices', [])
                if choices:
                    return choices[0].get('message', {}).get('content', '')
            return str(response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"LLM 调用失败: {str(e)}"


llm_client = LLMClient()


# ==================== 技术面分析模块 ====================
class TechnicalAnalyzer:
    """技术面分析器"""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def get_klines(self, timeframe: str = "4H", limit: int = 300) -> list:
        """
        获取 K 线数据

        Args:
            timeframe: 时间周期 (1H, 4H, 1D, 1W)
            limit: 获取数量

        Returns:
            K 线数据列表
        """
        url = f"{OKX_BASE_URL}/api/v5/market/history-candles"
        params = {
            "instId": self.symbol,
            "bar": timeframe,
            "limit": limit,
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("code") == "0":
                return data.get("data", [])
            logger.error(f"获取K线失败: {data}")
            return []
        except Exception as e:
            logger.error(f"获取K线异常: {e}")
            return []

    def calculate_ma(self, prices: list, period: int) -> Optional[float]:
        """计算移动平均线"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_rsi(self, prices: list, period: int = 14) -> Optional[float]:
        """计算 RSI 相对强弱指标"""
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, prices: list, period: int = 20) -> Optional[dict]:
        """计算布林带"""
        if len(prices) < period:
            return None

        recent_prices = prices[-period:]
        ma = sum(recent_prices) / period
        variance = sum((p - ma) ** 2 for p in recent_prices) / period
        std = variance ** 0.5

        upper_band = ma + 2 * std
        lower_band = ma - 2 * std

        return {
            "upper": upper_band,
            "middle": ma,
            "lower": lower_band,
            "current": prices[-1] if prices else None,
        }

    def analyze(self) -> dict:
        """
        执行技术面分析 - 仅返回客观数据指标（多周期：1H、4H、1D）

        Returns:
            技术分析结果字典
        """
        # 定义多周期
        timeframes = {
            "1H": {"limit": 48, "name": "1小时"},
            "4H": {"limit": 30, "name": "4小时"},
            "1D": {"limit": 30, "name": "日线"},
        }

        all_data = {}

        for tf, config in timeframes.items():
            data = self.get_klines(tf, config["limit"])
            if not data:
                continue

            closes = []
            for kline in data:
                if len(kline) >= 5:
                    closes.append(float(kline[4]))

            if not closes:
                continue

            # OKX API 返回的数据是最新在前，需要反转
            closes.reverse()

            current_price = closes[-1]
            ma5 = self.calculate_ma(closes, 5)
            ma10 = self.calculate_ma(closes, 10)
            ma20 = self.calculate_ma(closes, 20)
            rsi = self.calculate_rsi(closes, 14)
            bb = self.calculate_bollinger_bands(closes, 20)

            bb_position = None
            if bb and bb["upper"] and bb["lower"] and current_price:
                bb_range = bb["upper"] - bb["lower"]
                if bb_range > 0:
                    bb_position = round((current_price - bb["lower"]) / bb_range * 100, 2)

            all_data[tf] = {
                "current_price": round(current_price, 2),
                "ma5": round(ma5, 2) if ma5 else None,
                "ma10": round(ma10, 2) if ma10 else None,
                "ma20": round(ma20, 2) if ma20 else None,
                "rsi": round(rsi, 2) if rsi else None,
                "bollinger_upper": round(bb["upper"], 2) if bb and bb["upper"] else None,
                "bollinger_middle": round(bb["middle"], 2) if bb and bb["middle"] else None,
                "bollinger_lower": round(bb["lower"], 2) if bb and bb["lower"] else None,
                "bollinger_position": bb_position,
            }

        if not all_data:
            return {"error": "无法获取K线数据"}

        # 计算日线一周涨跌幅
        weekly_change = 0
        daily_data = self.get_klines("1D", 8)
        if len(daily_data) >= 8:
            price_now = float(daily_data[-1][4])
            price_week_ago = float(daily_data[0][4])
            weekly_change = round((price_now - price_week_ago) / price_week_ago * 100, 2)

        return {
            "symbol": self.symbol,
            "current_price": all_data.get("1D", {}).get("current_price", 0),
            "timeframes": all_data,
            "weekly_change": weekly_change,
        }


# ==================== 消息面分析模块 ====================
class NewsAnalyzer:
    """消息面分析器"""

    RSS_SOURCES = {
        "odaily": {
            "name": "Odaily星球日报",
            "url": "https://rss.odaily.news/rss/newsflash",
        }
    }

    def fetch_news(self, limit: int = 10) -> list:
        """
        获取加密货币新闻

        Args:
            limit: 获取数量

        Returns:
            新闻列表
        """
        news_list = []

        for source_key, source_info in self.RSS_SOURCES.items():
            try:
                response = requests.get(source_info["url"], timeout=10)
                import feedparser
                feed = feedparser.parse(response.text)

                if feed.entries:
                    for entry in feed.entries[:limit]:
                        news_list.append({
                            "source": source_info["name"],
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "description": entry.get("description", ""),
                            "pubDate": entry.get("pubDate", ""),
                        })
            except Exception as e:
                logger.error(f"获取新闻失败 {source_key}: {e}")

        return news_list[:limit]

    def summarize_news(self, news_list: list) -> str:
        """
        将新闻列表格式化为字符串

        Args:
            news_list: 新闻列表

        Returns:
            格式化的新闻字符串
        """
        if not news_list:
            return "暂无最新新闻"

        lines = ["【近期重要新闻】"]
        for i, news in enumerate(news_list[:10], 1):
            lines.append(f"{i}. {news['title']}")
            lines.append(f"描述: {news['description']}")
            lines.append(f"发布时间: {news['pubDate']}")

        return "\n".join(lines)


# ==================== 历史记录管理 ====================
class HistoryManager:
    """历史分析记录管理器"""

    def __init__(self):
        self.history_file = HISTORY_FILE
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def load_history(self) -> list:
        """加载历史分析记录"""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            return []

    def save_analysis(self, analysis_data: dict):
        """
        保存分析记录（详细版本）

        Args:
            analysis_data: 分析数据
        """
        history = self.load_history()

        tech_data = analysis_data.get("technical", {})

        # 添加详细记录
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": analysis_data.get("symbol", ""),
            # LLM 预测结果
            "prediction": analysis_data.get("prediction", ""),
            "confidence": analysis_data.get("confidence", ""),
            "reason": analysis_data.get("reason", ""),
            "target_price_range": analysis_data.get("target_price_range", ""),
            "risk_level": analysis_data.get("risk_level", ""),
            # 当前价格
            "current_price": tech_data.get("current_price", 0),
            "weekly_change": tech_data.get("weekly_change", 0),
            # 多周期技术指标
            "timeframes": {
                tf: {
                    "current_price": data.get("current_price", 0),
                    "ma5": data.get("ma5"),
                    "ma10": data.get("ma10"),
                    "ma20": data.get("ma20"),
                    "rsi": data.get("rsi"),
                    "bollinger_upper": data.get("bollinger_upper"),
                    "bollinger_middle": data.get("bollinger_middle"),
                    "bollinger_lower": data.get("bollinger_lower"),
                    "bollinger_position": data.get("bollinger_position"),
                }
                for tf, data in tech_data.get("timeframes", {}).items()
            },
        }

        history.append(record)

        # 只保留最近90天记录
        if len(history) > 90:
            history = history[-90:]

        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"分析记录已保存: {record['date']} - {record['prediction']}")
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")

    def get_last_prediction(self, symbol: str) -> Optional[dict]:
        """获取上一次的预测结果"""
        history = self.load_history()
        for record in reversed(history):
            if record.get("symbol") == symbol:
                return record
        return None


# ==================== Discord Webhook 推送 ====================
class DiscordNotifier:
    """Discord 消息推送器"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, content: str, embed: Optional[dict] = None):
        """
        发送消息到 Discord

        Args:
            content: 消息内容
            embed: 嵌入消息（可选）
        """
        if not self.webhook_url:
            logger.warning("未配置 Discord Webhook URL")
            print(content)
            return

        payload = {"content": content}
        if embed:
            payload["embeds"] = [embed]

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code == 204:
                logger.info("Discord 消息发送成功")
            else:
                logger.error(f"Discord 消息发送失败: {response.status_code}")
        except Exception as e:
            logger.error(f"Discord 推送异常: {e}")


# ==================== 主分析引擎 ====================
class TradingAnalyzer:
    """交易分析主引擎"""

    def __init__(self, symbol: str, webhook_url: str):
        self.symbol = symbol
        self.tech_analyzer = TechnicalAnalyzer(symbol)
        self.news_analyzer = NewsAnalyzer()
        self.history_manager = HistoryManager()
        self.notifier = DiscordNotifier(webhook_url)

    def generate_prompt(self, tech_data: dict, news_text: str, last_prediction: Optional[dict]) -> str:
        """
        生成 LLM 分析提示词 - 仅提供客观数据（多周期）

        Args:
            tech_data: 技术分析数据
            news_text: 新闻文本
            last_prediction: 上次预测（用于对比）

        Returns:
            完整的提示词
        """
        symbol = tech_data.get("symbol", "")
        current_price = tech_data.get("current_price", 0)
        timeframes = tech_data.get("timeframes", {})
        weekly_change = tech_data.get("weekly_change", 0)

        # 格式化多周期技术指标
        def format_tf_data(tf: str, data: dict) -> str:
            if not data:
                return f"{tf}: 无数据"
            return f"""{tf}:
  价格: ${data.get('current_price', 'N/A')}
  MA5: ${data.get('ma5', 'N/A')} | MA10: ${data.get('ma10', 'N/A')} | MA20: ${data.get('ma20', 'N/A')}
  RSI: {data.get('rsi', 'N/A')}
  布林带: ${data.get('bollinger_lower', 'N/A')} ~ ${data.get('bollinger_upper', 'N/A')} (位置: {data.get('bollinger_position', 'N/A')}%)"""

        tf_text = "\n".join([
            format_tf_data(tf, data)
            for tf, data in timeframes.items()
        ])

        # 上次预测对比
        last_pred_text = ""
        if last_prediction:
            last_pred_text = f"""
【上次预测 ({last_prediction.get('date', '')}】)
- 预测方向: {last_prediction.get('prediction', '')}
- 置信度: {last_prediction.get('confidence', '')}
- 当时价格: ${last_prediction.get('current_price', '')}
"""

        prompt = f"""你是一个专业的加密货币技术分析师。请根据以下多周期客观数据，独立判断并预测 {symbol} 的短期走势。

## 客观市场数据
- 当前价格(日线): ${current_price}
- 一周涨跌幅: {weekly_change}%

## 多周期技术指标（请自行分析判断）
{tf_text}

## 消息面
{news_text}

{last_pred_text}

## 输出要求
请根据以上所有数据，独立分析判断后输出JSON格式结果:
{{
    "prediction": "偏多/偏空/震荡",
    "confidence": "高/中/低",
    "reason": "分析理由",
    "target_price_range": "预期价格区间",
    "risk_level": "高/中/低"
}}

请只返回JSON，不要有其他内容。"""

        return prompt

    def analyze_and_notify(self):
        """执行分析并推送结果"""
        logger.info(f"开始分析 {self.symbol}")

        # 1. 技术面分析
        tech_data = self.tech_analyzer.analyze()
        if "error" in tech_data:
            logger.error(f"技术分析失败: {tech_data['error']}")
            return

        # 2. 消息面分析
        news_list = self.news_analyzer.fetch_news()
        news_text = self.news_analyzer.summarize_news(news_list)

        # 3. 获取上次预测
        last_prediction = self.history_manager.get_last_prediction(self.symbol)

        # 4. 生成提示词并调用 LLM
        prompt = self.generate_prompt(tech_data, news_text, last_prediction)
        llm_result = llm_client.analyze(prompt)

        # 5. 解析 LLM 结果
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{.*\}', llm_result, re.DOTALL)
            if json_match:
                prediction_data = json.loads(json_match.group())
            else:
                prediction_data = {"prediction": "震荡", "confidence": "中", "reason": "LLM解析失败"}
        except json.JSONDecodeError:
            logger.error(f"LLM 返回格式错误: {llm_result}")
            prediction_data = {"prediction": "震荡", "confidence": "中", "reason": "LLM解析错误"}

        # 6. 构建 Discord Embed
        embed = {
            "title": f"📈 {self.symbol} 行情分析预测",
            "color": 0x00FF00 if prediction_data.get("prediction") == "偏多" else 0xFF0000 if prediction_data.get("prediction") == "偏空" else 0xFFFF00,
            "fields": [
                {
                    "name": "🎯 预测方向",
                    "value": f"**{prediction_data.get('prediction', '震荡')}** (置信度: {prediction_data.get('confidence', '中')})",
                    "inline": False
                },
                {
                    "name": "1H 技术指标",
                    "value": f"MA5: ${tech_data.get('timeframes', {}).get('1H', {}).get('ma5', 'N/A')}\nMA10: ${tech_data.get('timeframes', {}).get('1H', {}).get('ma10', 'N/A')}\nRSI: {tech_data.get('timeframes', {}).get('1H', {}).get('rsi', 'N/A')}",
                    "inline": True
                },
                {
                    "name": "4H 技术指标",
                    "value": f"MA5: ${tech_data.get('timeframes', {}).get('4H', {}).get('ma5', 'N/A')}\nMA10: ${tech_data.get('timeframes', {}).get('4H', {}).get('ma10', 'N/A')}\nRSI: {tech_data.get('timeframes', {}).get('4H', {}).get('rsi', 'N/A')}",
                    "inline": True
                },
                {
                    "name": "1D 技术指标",
                    "value": f"MA5: ${tech_data.get('timeframes', {}).get('1D', {}).get('ma5', 'N/A')}\nMA10: ${tech_data.get('timeframes', {}).get('1D', {}).get('ma10', 'N/A')}\nMA20: ${tech_data.get('timeframes', {}).get('1D', {}).get('ma20', 'N/A')}\nRSI: {tech_data.get('timeframes', {}).get('1D', {}).get('rsi', 'N/A')}",
                    "inline": True
                },
                {
                    "name": "💰 当前价格",
                    "value": f"${tech_data.get('current_price', 0)}",
                    "inline": True
                },
                {
                    "name": "📉 一周涨跌",
                    "value": f"{tech_data.get('weekly_change', 0)}%",
                    "inline": True
                },
                {
                    "name": "📈 目标区间",
                    "value": prediction_data.get("target_price_range", "待定"),
                    "inline": True
                },
                {
                    "name": "⚠️ 风险等级",
                    "value": prediction_data.get("risk_level", "中"),
                    "inline": True
                },
                {
                    "name": "📝 分析理由",
                    "value": prediction_data.get("reason", "暂无")[:200],
                    "inline": False
                },
            ],
            "footer": {
                "text": f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源: OKX + RSS"
            }
        }

        # 7. 发送通知
        content = f"📊 每日行情分析报告 - {datetime.now().strftime('%Y-%m-%d')}"
        self.notifier.send(content, embed)

        # 8. 保存历史记录
        self.history_manager.save_analysis({
            "symbol": self.symbol,
            "prediction": prediction_data.get("prediction", ""),
            "confidence": prediction_data.get("confidence", ""),
            "reason": prediction_data.get("reason", ""),
            "target_price_range": prediction_data.get("target_price_range", ""),
            "risk_level": prediction_data.get("risk_level", ""),
            "technical": tech_data,
        })

        logger.info(f"分析完成: {self.symbol} - {prediction_data.get('prediction', '')}")


# ==================== 定时任务 ====================
def run_analysis():
    """执行分析任务"""
    for symbol in SYMBOLS:
        analyzer = TradingAnalyzer(symbol, WEBHOOK_URL)
        analyzer.analyze_and_notify()
        time.sleep(1)


def main():
    """主入口"""
    logger.info("=" * 50)
    logger.info("AI 交易分析系统启动")
    logger.info(f"分析交易对: {', '.join(SYMBOLS)}")
    logger.info(f"推送时间: 每天 {ANALYSIS_TIME}")
    logger.info("=" * 50)

    # 立即执行一次分析
    logger.info("执行初始分析...")
    run_analysis()

    # 设置定时任务
    scheduler = BlockingScheduler()
    # 解析 ANALYSIS_TIME (格式: "HH:MM")
    hour, minute = ANALYSIS_TIME.split(":")
    scheduler.add_job(run_analysis, CronTrigger(hour=int(hour), minute=int(minute)))

    logger.info(f"定时任务已设置: 每天 {ANALYSIS_TIME} 执行分析")

    # 启动调度器
    scheduler.start()


if __name__ == "__main__":
    main()
