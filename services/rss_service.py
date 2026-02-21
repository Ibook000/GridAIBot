"""
RSS 新闻服务模块
获取加密货币新闻快讯
"""
import feedparser
from datetime import datetime
from html.parser import HTMLParser


RSS_SOURCES = {
    "odaily": {
        "name": "Odaily星球日报",
        "url": "https://rss.odaily.news/rss/newsflash",
    }
}


class HTMLTextExtractor(HTMLParser):
    """
    HTML 文本提取器
    从 HTML 中提取纯文本内容
    """

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts).strip()


def strip_html(html_content: str) -> str:
    """
    移除 HTML 标签，提取纯文本

    Args:
        html_content: HTML 内容

    Returns:
        纯文本内容
    """
    if not html_content:
        return ""
    extractor = HTMLTextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


def fetch_news(source: str = "odaily", limit: int = 10) -> str:
    """
    获取 RSS 新闻快讯

    Args:
        source: 新闻源名称，默认 odaily
        limit: 返回新闻数量，默认 10 条

    Returns:
        格式化的新闻内容
    """
    if source not in RSS_SOURCES:
        available = ", ".join(RSS_SOURCES.keys())
        return f"未知的新闻源: {source}\n可用源: {available}"

    source_info = RSS_SOURCES[source]
    url = source_info["url"]
    source_name = source_info["name"]

    try:
        feed = feedparser.parse(url)

        if feed.bozo and feed.bozo_exception:
            return f"获取新闻失败: {feed.bozo_exception}"

        entries = feed.entries[:limit]

        if not entries:
            return f"暂无新闻快讯"

        lines = [f"{source_name}最新快讯:\n"]

        for i, entry in enumerate(entries, 1):
            title = entry.get("title", "无标题")
            link = entry.get("link", "")
            description = entry.get("description", "")
            pub_date = entry.get("pubDate", "")
            time_str = ""
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z") # pyright: ignore[reportArgumentType]
                    time_str = dt.strftime("%m-%d %H:%M")
                except ValueError:
                    time_str = pub_date

            lines.append(f"{i}. {title}")
            if time_str:
                lines.append(f"时间: {time_str}")
            if description:
                lines.append(f"{description}")
            lines.append(f"链接: {link}")

        return "\n".join(lines)

    except Exception as e:
        return f"获取新闻失败: {str(e)}"
