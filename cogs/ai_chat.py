"""
AI 对话命令模块
处理 @机器人 的消息，使用 AI 进行智能回复
支持定时任务创建和管理
"""
import uuid

import discord
from discord.ext import commands

from services import ai_service, scheduler_service, ScheduledTask


class AIChatCog(commands.Cog):
    """
    AI 对话命令组
    处理用户 @机器人 的消息
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chat_histories = {}
        scheduler_service.set_result_callback(self._on_task_result)

    async def _on_task_result(self, user_id: str, task_name: str, result: str):
        """
        定时任务执行结果回调
        向用户推送执行结果
        """
        try:
            user = await self.bot.fetch_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title=f"定时任务执行结果: {task_name}",
                    description=f"```\n{result[:2000]}\n```" if len(result) <= 2000 else f"```\n{result[:1990]}...\n```",
                    color=discord.Color.green() if "错误" not in result else discord.Color.red(),
                )
                await user.send(embed=embed)
        except Exception as e:
            print(f"[ERROR] 推送任务结果失败: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        监听消息事件，处理 @机器人 的消息
        """
        if message.author.bot:
            return

        if self.bot.user in message.mentions:
            print(f"[INFO] 机器人被 @{message.author.name} (ID: {message.author.id}) 提及")
            print(f"[INFO] 消息内容: {message.content[:100]}{'...' if len(message.content) > 100 else ''}")
            await self._handle_ai_chat(message)

    async def _handle_ai_chat(self, message: discord.Message):
        """
        处理 AI 对话
        """
        user_id = str(message.author.id)
        print(f"[INFO] 处理用户 {message.author.name} (ID: {user_id}) 的请求")

        user_input = message.content
        for mention in message.mentions:
            user_input = user_input.replace(mention.mention, "").strip()

        if not user_input:
            print("[INFO] 用户输入为空，发送欢迎消息")
            await message.reply("你好！有什么我可以帮助你的吗？你可以问我关于持仓、网格策略或账户余额的问题，也可以创建定时任务（如：每天早上 8 点查询 BTC 持仓）。")
            return

        print(f"[INFO] 清洗后的用户输入: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        async with message.channel.typing():
            print(f"[INFO] 调用 AI 分析用户请求...")
            schedule_task = await ai_service.analyze_schedule_task(user_input)

            if schedule_task:
                print(f"[INFO] 检测到定时任务请求: {schedule_task.get('task_name')}")
                print(f"[INFO] 任务类型: {schedule_task.get('schedule', {}).get('type', 'unknown')}")
                await self._handle_schedule_task(message, user_id, user_input, schedule_task)
            else:
                print(f"[INFO] 判定为普通对话，转入 AI 聊天处理")
                await self._handle_normal_chat(message, user_id, user_input)

    async def _handle_schedule_task(
        self,
        message: discord.Message,
        user_id: str,
        user_input: str,
        schedule_task: dict,
    ):
        """
        处理定时任务创建
        """
        try:
            task_name = schedule_task.get('task_name', '未命名任务')
            print(f"[INFO] ========== 开始创建定时任务 ==========")
            print(f"[INFO] 任务名称: {task_name}")
            print(f"[INFO] 调度类型: {schedule_task.get('schedule', {}).get('type', 'unknown')}")
            print(f"[INFO] 原始脚本长度: {len(schedule_task.get('script', ''))} 字符")
            
            script = schedule_task["script"]
            max_retries = 2

            for attempt in range(max_retries + 1):
                print(f"[INFO] --- 验证脚本 (尝试 {attempt + 1}/{max_retries + 1}) ---")
                await message.channel.typing()
                success, result = await scheduler_service.validate_script(script)

                if success:
                    print(f"[INFO] 脚本验证通过")
                    break

                if attempt < max_retries:
                    print(f"[INFO] 脚本验证失败，尝试修复...")
                    print(f"[INFO] 错误信息: {result[:200]}...")
                    await message.channel.typing()
                    fix_result = await ai_service.fix_script(script, result, user_input)

                    if fix_result and fix_result.get("script"):
                        script = fix_result["script"]
                        print(f"[INFO] 修复后的脚本长度: {len(script)} 字符")
                        await message.reply(f"脚本验证失败，AI 正在尝试修复... (尝试 {attempt + 2}/{max_retries + 1})")
                    else:
                        print(f"[INFO] AI 无法修复脚本")
                        break
                else:
                    print(f"[ERROR] 脚本验证失败，已达最大重试次数")
                    embed = discord.Embed(
                        title="定时任务创建失败",
                        description=f"脚本验证未通过，已尝试自动修复但仍失败。\n\n**错误信息:**\n```\n{result[:500]}\n```",
                        color=discord.Color.red(),
                    )
                    embed.add_field(
                        name="提示",
                        value="请尝试简化任务描述，或联系管理员。",
                        inline=False,
                    )
                    await message.reply(embed=embed)
                    return

            schedule_task["script"] = script
            max_runs = schedule_task.get("max_runs", 0)
            task = ScheduledTask(
                str(uuid.uuid4()),
                schedule_task["task_name"],
                user_id,
                schedule_task["schedule"],
                schedule_task["script"],
                max_runs=max_runs,
            )

            print(f"[INFO] 添加任务到调度器...")
            await scheduler_service.add_task(task)
            print(f"[INFO] 定时任务创建成功! 任务ID: {task.id}")

            schedule_desc = self._format_schedule(schedule_task["schedule"])

            embed = discord.Embed(
                title="定时任务已创建",
                color=discord.Color.green(),
            )
            embed.add_field(name="任务名称", value=task.name, inline=True)
            embed.add_field(name="执行计划", value=schedule_desc, inline=True)
            embed.add_field(name="任务ID", value=f"`{task.id}`", inline=False)
            embed.set_footer(text="使用 !tasks 查看任务列表，使用 !task_delete <id> 删除任务")

            await message.reply(embed=embed)

        except Exception as e:
            await message.reply(f"创建定时任务失败: {str(e)}")

    def _format_schedule(self, schedule: dict) -> str:
        """
        格式化调度信息为可读文本
        """
        schedule_type = schedule.get("type", "cron")

        if schedule_type == "cron":
            cron = schedule.get("cron", "")
            return f"Cron: `{cron}`"
        elif schedule_type == "interval":
            if "hours" in schedule:
                return f"每 {schedule['hours']} 小时"
            elif "minutes" in schedule:
                return f"每 {schedule['minutes']} 分钟"
            elif "days" in schedule:
                return f"每 {schedule['days']} 天"
            else:
                return str(schedule)

        return str(schedule)

    async def _handle_normal_chat(self, message: discord.Message, user_id: str, user_input: str):
        """
        处理普通 AI 对话
        """
        chat_history = self.chat_histories.get(user_id, [])
        history_len = len(chat_history)
        print(f"[INFO] ========== 处理普通对话 ==========")
        print(f"[INFO] 当前对话历史长度: {history_len} 条")
        print(f"[INFO] 正在调用 AI 服务...")
        
        response = await ai_service.chat(user_input, chat_history)
        
        print(f"[INFO] AI 响应长度: {len(response)} 字符")
        
        self.chat_histories[user_id] = chat_history + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response},
        ]

        if len(self.chat_histories[user_id]) > 20:
            self.chat_histories[user_id] = self.chat_histories[user_id][-20:]
            print(f"[INFO] 对话历史已裁剪至 20 条")

        await message.reply(response)

    @commands.command(name="clear")
    async def clear_history(self, ctx: commands.Context):
        """
        清除对话历史
        用法: !clear
        """
        user_id = str(ctx.author.id)
        print(f"[INFO] 用户 {ctx.author.name} (ID: {user_id}) 执行 !clear 命令")
        if user_id in self.chat_histories:
            del self.chat_histories[user_id]
            print(f"[INFO] 已清除用户 {user_id} 的对话历史")
            await ctx.send("对话历史已清除。")
        else:
            print(f"[INFO] 用户 {user_id} 无对话历史可清除")
            await ctx.send("暂无对话历史。")

    @commands.command(name="tasks")
    async def list_tasks(self, ctx: commands.Context):
        """
        查看当前用户的定时任务列表
        用法: !tasks
        """
        user_id = str(ctx.author.id)
        print(f"[INFO] 用户 {ctx.author.name} (ID: {user_id}) 执行 !tasks 命令")
        tasks = scheduler_service.get_tasks(user_id)

        if not tasks:
            print(f"[INFO] 用户 {user_id} 没有任何定时任务")
            await ctx.send("您还没有创建任何定时任务。")
            return

        print(f"[INFO] 用户 {user_id} 共有 {len(tasks)} 个定时任务")
        embed = discord.Embed(
            title="您的定时任务",
            color=discord.Color.blue(),
        )

        for task in tasks:
            status = "已启用" if task["enabled"] else "已禁用"
            schedule_desc = self._format_schedule(task["schedule"])
            embed.add_field(
                name=f"{task['name']} ({status})",
                value=f"ID: `{task['id']}`\n执行计划: {schedule_desc}",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="task_delete")
    async def delete_task(self, ctx: commands.Context, task_id: str):
        """
        删除定时任务
        用法: !task_delete <任务ID>
        """
        user_id = str(ctx.author.id)
        print(f"[INFO] 用户 {ctx.author.name} (ID: {user_id}) 执行 !task_delete 命令，任务ID: {task_id}")
        tasks = scheduler_service.get_tasks(user_id)

        task = next((t for t in tasks if t["id"] == task_id), None)

        if not task:
            print(f"[INFO] 未找到任务 ID: {task_id}")
            await ctx.send(f"未找到任务 ID: {task_id}")
            return

        print(f"[INFO] 正在删除任务: {task['name']} (ID: {task_id})")
        success = await scheduler_service.remove_task(task_id)

        if success:
            print(f"[INFO] 任务 {task_id} 删除成功")
            await ctx.send(f"已删除任务: {task['name']}")
        else:
            print(f"[ERROR] 任务 {task_id} 删除失败")
            await ctx.send("删除任务失败")


async def setup(bot: commands.Bot):
    """
    Cog 加载入口函数
    """
    await bot.add_cog(AIChatCog(bot))
