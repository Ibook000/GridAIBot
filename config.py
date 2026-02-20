"""
配置文件
支持从环境变量读取敏感配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# OKX
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_API_SECRET = os.getenv("OKX_API_SECRET", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")

BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com")
OKX_FLAG = os.getenv("OKX_FLAG", "0")

# LLM 配置
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://apis.iflow.cn/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-max")
