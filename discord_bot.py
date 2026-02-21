"""
Discord Bot 主入口文件
使用 Cogs 扩展系统，便于模块化管理命令
"""
import discord
from discord.ext import commands

from config import DISCORD_BOT_TOKEN


class GridAIBot(commands.Bot):
    """
    GridAI Bot 主类
    继承自 discord.ext.commands.Bot
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """
        Bot 启动时的初始化钩子
        自动加载所有 Cog 模块
        """
        # 加载 Cog 模块
        cogs = [
            "cogs.position",
            "cogs.grid",
            "cogs.ai_chat",
            "cogs.balance",
            "cogs.news",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"[OK] 已加载模块: {cog}")
            except Exception as e:
                print(f"[ERROR] 加载模块失败 {cog}: {e}")

    async def on_ready(self):
        """
        Bot 连接成功时的回调
        """
        print(f"[OK] 机器人已上线: {self.user}")
        print(f"[INFO] 命令前缀: {self.command_prefix}")
        print(f"[INFO] 已加载 {len(self.cogs)} 个命令模块")


def main():
    """
    程序入口
    """
    bot = GridAIBot()
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
