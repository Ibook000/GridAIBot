"""
OKX LangChain 工具模块
将 OKX 操作封装为 LangChain 工具，供 AI Agent 调用
"""
from langchain_core.tools import tool

from .queries import (
    query_swap_positions,
    query_grid_strategies,
    query_martingale_strategies,
    query_account_balance,
    query_candlesticks,
)
from services.rss_service import fetch_news


@tool
def get_swap_positions() -> str:
    """
    查询当前合约持仓信息。
    返回所有非零的合约持仓详情，包括方向、数量、均价、未实现盈亏、杠杆等。
    当用户询问持仓、仓位、持有合约等信息时使用此工具。
    """
    return query_swap_positions()


@tool
def get_grid_strategies() -> str:
    """
    查询合约网格策略信息。
    返回所有运行中的合约网格策略详情，包括方向、杠杆、网格区间、盈亏等。
    当用户询问网格策略、网格交易、网格机器人等信息时使用此工具。
    """
    return query_grid_strategies()


@tool
def get_martingale_strategies() -> str:
    """
    查询合约马丁格尔策略信息。
    返回所有运行中的合约马丁格尔策略详情，包括方向、杠杆、总盈亏、已捕获收益等。
    当用户询问马丁格尔策略、马丁策略、合约马丁格尔等信息时使用此工具。
    """
    return query_martingale_strategies()


@tool
def get_account_balance() -> str:
    """
    查询账户余额信息。
    返回账户的总权益、可用余额等信息。
    当用户询问余额、账户资金、可用金额等信息时使用此工具。
    """
    return query_account_balance()


@tool
def get_candlesticks(inst_id: str, bar: str = "1H", limit: int = 20) -> str:
    """
    查询K线数据。
    返回指定交易对的K线数据，包括开盘价、最高价、最低价、收盘价、成交量等。
    当用户询问K线、行情走势、价格历史等信息时使用此工具。

    Args:
        inst_id: 产品ID，如 BTC-USDT-SWAP、ETH-USDT-SWAP
        bar: K线周期，支持 1m/5m/15m/1H/4H/1D/1W/1M，默认1H
        limit: 返回数量，默认20条
    """
    return query_candlesticks(inst_id, bar, limit)


@tool
def get_crypto_news(limit: int = 5) -> str:
    """
    获取加密货币新闻快讯。
    返回最新的加密货币行业新闻和快讯。
    当用户询问新闻、快讯、行业动态、最新消息等信息时使用此工具。

    Args:
        limit: 返回新闻数量，默认5条
    """
    return fetch_news(limit=limit)


OKX_TOOLS = [
    get_swap_positions,
    get_grid_strategies,
    get_martingale_strategies,
    get_account_balance,
    get_candlesticks,
    get_crypto_news,
]
