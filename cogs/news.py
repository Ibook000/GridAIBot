"""
新闻快讯命令模块
提供加密货币新闻相关的 Discord 命令
"""
import discord
from discord.ext import commands

from services import fetch_news, RSS_SOURCES


class NewsCog(commands.Cog):
    """
    新闻快讯命令组
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="news")
    async def news(self, ctx: commands.Context, limit: int = 10):
        """
        获取加密货币新闻快讯
        用法: !news [数量]
        示例: !news 5
        """
        await ctx.send("正在获取加密货币新闻快讯...")
        try:
            result = fetch_news(limit=limit)
            if len(result) > 2000:
                chunks = []
                current_chunk = ""
                for line in result.split("\n"):
                    if len(current_chunk) + len(line) + 1 > 2000:
                        chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk += "\n" + line if current_chunk else line
                if current_chunk:
                    chunks.append(current_chunk)

                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await ctx.send(chunk)
                    else:
                        await ctx.send(chunk)
            else:
                await ctx.send(result)
        except Exception as e:
            await ctx.send(f"获取新闻失败: {e}")

    @commands.command(name="sources")
    async def sources(self, ctx: commands.Context):
        """
        显示可用的新闻源
        用法: !sources
        """
        lines = ["可用的新闻源:"]
        for key, info in RSS_SOURCES.items():
            lines.append(f"- {key}: {info['name']}")
        await ctx.send("\n".join(lines))


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(NewsCog(bot))
