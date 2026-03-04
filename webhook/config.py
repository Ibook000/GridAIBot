"""
AI 交易分析脚本 - 独立配置文件
复制此文件为 config.py 并填入你的配置
"""
import os
from pathlib import Path

# ==================== Discord Webhook 配置 ====================
# 在 Discord 服务器设置 -> 整合 -> Webhook 创建
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ==================== 交易分析配置 ====================
# 分析的交易对（多个用逗号分隔）
TRADING_SYMBOLS = os.getenv("TRADING_SYMBOLS", "BTC-USDT-SWAP").split(",")

# 每日分析推送时间（24小时制，格式: HH:MM）
TRADING_ANALYSIS_TIME = os.getenv("TRADING_ANALYSIS_TIME", "09:00")

# ==================== OKX API 配置 ====================
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_API_SECRET = os.getenv("OKX_API_SECRET", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com")
OKX_FLAG = os.getenv("OKX_FLAG", "0")

# ==================== LLM 配置 ====================
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-max")
