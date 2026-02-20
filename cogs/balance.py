"""
余额查询命令模块
提供账户余额相关的 Discord 命令
"""
import discord
from discord.ext import commands

from okx_queries import query_account_balance


class BalanceCog(commands.Cog):
    """
    余额查询命令组
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bal")
    async def balance(self, ctx: commands.Context):
        """
        查询账户余额
        用法: !bal
        """
        await ctx.send("正在查询 OKX 账户余额...")
        try:
            result = query_account_balance()
            await ctx.send(result)
        except Exception as e:
            await ctx.send(f"查询失败: {e}")


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(BalanceCog(bot))
