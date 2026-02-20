"""
网格策略命令模块
提供合约网格策略相关的 Discord 命令
"""
import discord
from discord.ext import commands

from okx_queries import query_grid_strategies


class GridCog(commands.Cog):
    """
    网格策略命令组
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="grid")
    async def grid(self, ctx: commands.Context):
        """
        查询合约网格策略
        用法: !grid
        """
        await ctx.send("正在查询 OKX 合约网格策略...")
        try:
            result = query_grid_strategies()
            await ctx.send(result)
        except Exception as e:
            await ctx.send(f"查询失败: {e}")


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(GridCog(bot))
