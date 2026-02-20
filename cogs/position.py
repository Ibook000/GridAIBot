"""
持仓查询命令模块
提供合约持仓相关的 Discord 命令
"""
import discord
from discord.ext import commands

from okx_queries import query_swap_positions


class PositionCog(commands.Cog):
    """
    持仓查询命令组
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="pos")
    async def position(self, ctx: commands.Context):
        """
        查询当前合约持仓
        用法: !pos
        """
        await ctx.send("正在查询 OKX 合约仓位...")
        try:
            result = query_swap_positions()
            await ctx.send(result)
        except Exception as e:
            await ctx.send(f"查询失败: {e}")


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(PositionCog(bot))
