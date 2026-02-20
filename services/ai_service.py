# pyright: reportArgumentType=false, reportGeneralTypeIssues=false
"""
AI 服务模块
使用 LangChain + LangGraph 实现 AI 对话功能
"""
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain.agents import create_agent

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from tools import OKX_TOOLS


# 系统提示词
SYSTEM_PROMPT = """你是一个专业的加密货币交易助手，有敏锐的市场嗅觉分析能力。

你可以使用以下工具来帮助用户：
1. get_swap_positions - 查询合约持仓信息
2. get_grid_strategies - 查询网格策略
3. get_account_balance - 查询账户余额
4. get_candlesticks - 查询K线数据，需要提供产品ID(如BTC-USDT-SWAP)、周期(如1H/4H/1D)、数量

当用户询问持仓、网格策略、余额、K线行情等信息时，请调用相应的工具获取实时数据。

请用中文回复，保持简洁专业。如果用户的问题与交易无关，请礼貌地说明你只能帮助处理交易相关的问题。
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
                    messages.append(SystemMessage(content=content))

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
