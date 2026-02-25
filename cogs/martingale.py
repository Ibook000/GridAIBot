"""
马丁格尔策略命令模块
提供合约马丁格尔策略相关的 Discord 命令
"""
import discord
from discord.ext import commands

from okx_api import query_martingale_strategies


class MartingaleCog(commands.Cog):
    """
    马丁格尔策略命令组
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="martingale", aliases=["martin", "dca"])
    async def martingale(self, ctx: commands.Context):
        """
        查询合约马丁格尔策略
        用法: !martingale 或 !martin 或 !dca
        """
        await ctx.send("正在查询 OKX 合约马丁格尔策略...")
        try:
            result = query_martingale_strategies()
            await ctx.send(result)
        except Exception as e:
            await ctx.send(f"查询失败: {e}")


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(MartingaleCog(bot))
