"""
AI 对话命令模块
处理 @机器人 的消息，使用 AI 进行智能回复
"""
import discord
from discord.ext import commands

from services import ai_service


class AIChatCog(commands.Cog):
    """
    AI 对话命令组
    处理用户 @机器人 的消息
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chat_histories = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        监听消息事件，处理 @机器人 的消息
        """
        if message.author.bot:
            return

        if self.bot.user in message.mentions:
            await self._handle_ai_chat(message)

    async def _handle_ai_chat(self, message: discord.Message):
        """
        处理 AI 对话
        """
        user_id = str(message.author.id)

        user_input = message.content
        for mention in message.mentions:
            user_input = user_input.replace(mention.mention, "").strip()

        if not user_input:
            await message.reply("你好！有什么我可以帮助你的吗？你可以问我关于持仓、网格策略或账户余额的问题。")
            return

        async with message.channel.typing():
            chat_history = self.chat_histories.get(user_id, [])
            response = await ai_service.chat(user_input, chat_history)

            self.chat_histories[user_id] = chat_history + [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response},
            ]

            if len(self.chat_histories[user_id]) > 20:
                self.chat_histories[user_id] = self.chat_histories[user_id][-20:]

            await message.reply(response)

    @commands.command(name="clear")
    async def clear_history(self, ctx: commands.Context):
        """
        清除对话历史
        用法: !clear
        """
        user_id = str(ctx.author.id)
        if user_id in self.chat_histories:
            del self.chat_histories[user_id]
            await ctx.send("对话历史已清除。")
        else:
            await ctx.send("暂无对话历史。")


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(AIChatCog(bot))
