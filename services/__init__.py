"""
服务模块
"""
from .ai_service import AIService, ai_service
from .rss_service import fetch_news,  RSS_SOURCES

__all__ = [
    "AIService",
    "ai_service",
    "fetch_news",
    "RSS_SOURCES",
]
