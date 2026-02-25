# pyright: reportArgumentType=false, reportGeneralTypeIssues=false
"""
AI 服务模块
使用 LangChain + LangGraph 实现 AI 对话功能
支持定时任务识别和生成
"""
import json
import re
from typing import Any, Optional

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langchain.agents import create_agent

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from okx_api.tools import OKX_TOOLS


# 系统提示词
SYSTEM_PROMPT = """你是一个专业的加密货币交易助手，有敏锐的市场嗅觉分析能力。

你可以使用以下工具来帮助用户：
1. get_swap_positions - 查询合约持仓信息
2. get_grid_strategies - 查询网格策略
3. get_account_balance - 查询账户余额
4. get_candlesticks - 查询K线数据，需要提供产品ID(如BTC-USDT-SWAP)、周期(如1H/4H/1D)、k线数量
5. get_crypto_news - 获取加密货币新闻快讯，当用户询问新闻、快讯、行业动态时使用

当用户询问持仓、网格策略、余额、K线行情、新闻快讯等信息时，请调用相应的工具获取实时数据。

请用中文回复，保持简洁专业。如果用户的问题与交易无关，请礼貌地说明你只能帮助处理交易相关的问题。
"""

# 定时任务系统提示词
SCHEDULE_TASK_PROMPT = """你是一个定时任务分析助手。你的任务是根据用户的描述，判断是否为定时任务，并生成相应的 schedule（调度配置）和 script（执行脚本）。

## 判断规则
- 如果用户要求"每天几点"、"每周几号"、"每小时"、"每分钟"等定时执行的操作，那就是定时任务
- 如果用户只是普通的查询请求，不是定时任务，返回 {"is_schedule_task": false}

## Schedule 格式 (JSON)

### Cron 类型 (type: "cron")
使用 Cron 表达式，格式为 "分 时 日 月 周"
例如：
- "0 8 * * *" = 每天 8:00
- "0 9 * * 1-5" = 每周一到周五 9:00
- "30 18 * * *" = 每天 18:30
- "0 */6 * * *" = 每 6 小时

### Interval 类型 (type: "interval")
使用间隔时间，单位：seconds, minutes, hours, days
例如：
- {"type": "interval", "hours": 1} = 每小时
- {"type": "interval", "minutes": 30} = 每 30 分钟
- {"type": "interval", "days": 1} = 每天

## Script 格式
1. Python 脚本，使用标准库 + requests 库（需要安装：pip install requests）
2. OKX 公共 API 示例：
获取单个	GET https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT
获取K线	    GET https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1H&limit=100
获取深度	GET https://www.okx.com/api/v5/market/books?instId=BTC-USDT&sz=20
3. 脚本需要返回文本结果，用于向用户推送
4. **重要**: print() 语句中的字符串如果包含换行，必须使用三引号 包裹，并在字符串前加 f 前缀
5. script 中的 print() 内容就是推送给用户的最终结果

## 条件提醒 (重要!)
如果用户要求"满足条件时提醒"、"超过阈值时通知"等条件提醒：
- 脚本需要自己判断条件是否满足
- 条件满足时才用 print() 输出内容
- 条件不满足时不要 print()（或 print() 输出空/无意义内容）
- 这样调度器就不会发送消息，实现"触发条件再发信息"

## 执行次数限制
如果用户要求"提醒一次"、"提醒 N 次"、"到了就停止"等一次性提醒：
- 在返回的 JSON 中添加 max_runs 字段
- max_runs 表示执行次数上限，达到后任务自动移除
- 例如：max_runs: 1 表示执行 1 次后自动删除
- 如果没有设置 max_runs 或 max_runs <= 0，则表示无限次执行

## 示例

用户: "每天早上 8 点查询 BTC 价格"
返回:
{
  "is_schedule_task": true,
  "schedule": {"type": "cron", "cron": "0 8 * * *"},
  "script": "import requests\\nurl = 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT'\\nresp = requests.get(url).json()\\ndata = resp['data'][0] if resp.get('data') else {}\\nprint(f'BTC 当前价格: {data.get(\"last\", \"N/A\")} USDT')",
  "task_name": "BTC 价格监控"
}

用户: "每小时提醒我看行情"
返回:
{
  "is_schedule_task": true,
  "schedule": {"type": "interval", "hours": 1},
  "script": "import requests\\nurl = 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT'\\nresp = requests.get(url).json()\\ndata = resp['data'][0] if resp.get('data') else {}\\nprint(f'BTC: {data.get(\"last\", \"N/A\")}')",
  "task_name": "行情提醒"
}

用户: "查询哪些币种资金费率变化大"
返回:
{
  "is_schedule_task": true,
  "schedule": {"type": "cron", "cron": "0 */4 * * *"},
  "script": "import requests\\nurl = 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT'\\nresp = requests.get(url).json()\\ndata = resp['data'][0] if resp.get('data') else {}\\nprint(f'''以下币种资金费率变化超过0.5%:\\nBTC-USDT: {data.get(\"last\", \"N/A\")}''')",
  "task_name": "资金费率监控"
}

用户: "帮我查一下当前 BTC 价格"
返回:
{"is_schedule_task": false}

## 输出要求
- 只返回 JSON，不要有其他内容
- 如果是定时任务，必须包含: is_schedule_task=true, schedule, script, task_name
- 如果不是定时任务，只返回: {"is_schedule_task": false}
- script 中的 print() 内容就是推送给用户的最终结果
- 合理命名 task_name（任务名称）
- script 需要转义换行符为 \\n
- 直接使用 requests 
"""


class AIService:
    """
    AI 服务类
    封装 LangChain Agent 功能
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._llm = None
        self._agent = None
        self._initialized = True

    @property
    def llm(self) -> ChatOpenAI:
        """
        获取 LLM 实例
        """
        if self._llm is None:
            self._llm = ChatOpenAI(
                base_url=LLM_BASE_URL,
                api_key=SecretStr(LLM_API_KEY),
                model=LLM_MODEL,
                temperature=0.7,
            )
        return self._llm

    @property
    def agent(self):
        """
        获取 Agent 实例
        """
        if self._agent is None:
            self._agent = create_agent(
                self.llm,
                OKX_TOOLS,
            )
        return self._agent

    def _parse_schedule_result(self, text: str) -> Optional[dict[str, Any]]:
        """
        解析 AI 返回的定时任务 JSON

        Args:
            text: AI 返回的文本

        Returns:
            解析后的字典，如果解析失败返回 None
        """
        try:
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group())  # type: ignore
                return data
        except json.JSONDecodeError:
            pass
        return None

    async def analyze_schedule_task(self, user_input: str) -> Optional[dict[str, Any]]:
        """
        分析用户输入是否为定时任务请求

        Args:
            user_input: 用户输入

        Returns:
            如果是定时任务，返回包含 schedule, script, task_name 的字典
            如果不是定时任务，返回 None
        """
        messages = [
            SystemMessage(content=SCHEDULE_TASK_PROMPT),
            HumanMessage(content=f"用户: {user_input}"),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content

            result = self._parse_schedule_result(content)

            if result and result.get("is_schedule_task") is True:
                return {
                    "schedule": result.get("schedule"),
                    "script": result.get("script"),
                    "task_name": result.get("task_name", "定时任务"),
                }

            return None

        except Exception as e:
            print(f"[ERROR] 分析定时任务失败: {e}")
            return None

    FIX_SCRIPT_PROMPT = """你是一个 Python 脚本修复助手。

用户尝试创建一个定时任务，但脚本执行失败了。请根据错误信息修复脚本。

## 修复要求
1. 只使用 Python 标准库和 requests 库，不要使用其他第三方库
2. 使用 requests 库发送 HTTP 请求获取数据
3. OKX 公共 API 示例：
   - 获取行情：GET https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT
   - 获取K线：GET https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1H&limit=100
4. 脚本需要返回文本结果，用于向用户推送
5. **重要**: print() 语句中的字符串如果包含换行，必须使用三引号包裹，并在字符串前加 f 前缀
6. script 中的 print() 内容就是推送给用户的最终结果
7. script 需要转义换行符为 \\n

## 输出要求
- 只返回 JSON，不要有其他内容
- 返回格式: {"script": "修复后的脚本", "reason": "修复原因简述"}
- script 中使用单引号 ' 包裹字符串，内部使用双引号 "
"""

    async def fix_script(self, original_script: str, error_message: str, user_request: str) -> Optional[dict[str, Any]]:
        """
        修复脚本

        Args:
            original_script: 原始脚本
            error_message: 错误信息
            user_request: 用户原始请求

        Returns:
            修复后的脚本信息
        """
        messages = [
            SystemMessage(content=self.FIX_SCRIPT_PROMPT),
            HumanMessage(
                content=f"用户请求: {user_request}\n\n"
                f"原始脚本:\n{original_script}\n\n"
                f"执行错误:\n{error_message}\n\n"
                f"请修复脚本。"
            ),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content

            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                result = json.loads(json_match.group())  # type: ignore
                return {
                    "script": result.get("script"),
                    "reason": result.get("reason", "已修复"),
                }

            return None

        except Exception as e:
            print(f"[ERROR] 修复脚本失败: {e}")
            return None

    async def chat(self, user_input: str, chat_history: list | None = None) -> str:
        """
        与 AI 进行对话 (异步方法)

        Args:
            user_input: 用户输入
            chat_history: 对话历史 (可选)

        Returns:
            AI 回复内容
        """
        messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_input))

        try:
            result = await self.agent.ainvoke({"messages": messages})
            output_messages = result.get("messages", [])
            if output_messages:
                last_message = output_messages[-1]
                return last_message.content
            return "抱歉，我无法处理您的请求。"
        except Exception as e:
            return f"处理请求时出错: {str(e)}"


ai_service = AIService()
