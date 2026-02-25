"""
OKX 数据查询模块
封装 OKX 数据查询，直接返回格式化文本
"""
from datetime import datetime

from .client import okx_client


def query_swap_positions() -> str:
    """
    查询合约持仓

    Returns:
        格式化的持仓信息文本
    """
    account = okx_client.account
    res = account.get_positions()
    data = res.get("data", [])

    positions = []
    for p in data:
        if not p["instId"].endswith("SWAP"):
            continue
        if float(p["pos"]) == 0:
            continue

        direction = "多" if p["posSide"] == "long" else "空"
        upl = float(p["upl"])
        positions.append({
            "inst_id": p["instId"],
            "direction": direction,
            "pos": p["pos"],
            "avg_px": p["avgPx"],
            "upl": upl,
            "lever": p["lever"],
        })

    if not positions:
        return "当前无任何合约持仓"

    lines = ["当前合约持仓:"]
    for pos in positions:
        upl_str = f"+{pos['upl']:.2f}" if pos['upl'] >= 0 else f"{pos['upl']:.2f}"
        lines.append(
            f"- {pos['inst_id']}: {pos['direction']}方, "
            f"数量: {pos['pos']}, 均价: {pos['avg_px']}, "
            f"未实现盈亏: {upl_str} USDT, 杠杆: {pos['lever']}x"
        )

    return "\n".join(lines)


def query_grid_strategies() -> str:
    """
    查询合约网格策略

    Returns:
        格式化的网格策略信息文本
    """
    grid_api = okx_client.grid
    res = grid_api.grid_orders_algo_pending(algoOrdType="contract_grid")
    data = res.get("data", [])

    if not data:
        return "当前无运行中的合约网格策略"

    state_map = {
        "running": "运行中",
        "paused": "已暂停",
        "stopped": "已停止",
    }

    direction_map = {
        "long": "做多",
        "short": "做空",
    }

    lines = ["合约网格策略列表:"]
    for g in data:
        inst_id = g.get("instId", "N/A")
        state = state_map.get(g.get("state", ""), g.get("state", ""))
        direction = direction_map.get(g.get("direction", ""), g.get("direction", ""))
        lever = g.get("lever", "N/A")
        actual_lever = g.get("actualLever", "")
        grid_num = g.get("gridNum", "N/A")
        min_px = g.get("minPx", "N/A")
        max_px = g.get("maxPx", "N/A")
        total_pnl = float(g.get("totalPnl", "0"))
        float_profit = float(g.get("floatProfit", "0"))
        grid_profit = float(g.get("gridProfit", "0"))
        pnl_ratio = float(g.get("pnlRatio", "0")) * 100
        liq_px = g.get("liqPx", "N/A")

        lever_text = f"{lever}x"
        if actual_lever:
            try:
                lever_text = f"{lever}x(实际{float(actual_lever):.2f}x)"
            except ValueError:
                pass

        total_pnl_str = f"+{total_pnl:.2f}" if total_pnl >= 0 else f"{total_pnl:.2f}"
        float_profit_str = f"+{float_profit:.2f}" if float_profit >= 0 else f"{float_profit:.2f}"
        grid_profit_str = f"+{grid_profit:.2f}" if grid_profit >= 0 else f"{grid_profit:.2f}"
        pnl_ratio_str = f"+{pnl_ratio:.2f}%" if pnl_ratio >= 0 else f"{pnl_ratio:.2f}%"

        lines.append(
            f"- {inst_id} ({state}):\n"
            f"  方向: {direction}, 杠杆: {lever_text}\n"
            f"  网格区间: {min_px} ~ {max_px}, 网格数: {grid_num}\n"
            f"  总盈亏: {total_pnl_str} USDT, 浮动盈亏: {float_profit_str}\n"
            f"  网格收益: {grid_profit_str}, 收益率: {pnl_ratio_str}\n"
            f"  爆仓价: {liq_px}"
        )

    return "\n".join(lines)


def query_martingale_strategies() -> str:
    """
    查询合约马丁格尔策略

    Returns:
        格式化的马丁格尔策略信息文本
    """
    grid_api = okx_client.grid
    res = grid_api.grid_orders_algo_pending(algoOrdType="contract_martingale")
    data = res.get("data", [])

    if not data:
        return "当前无运行中的合约马丁格尔策略"

    state_map = {
        "running": "运行中",
        "paused": "已暂停",
        "stopped": "已停止",
    }

    direction_map = {
        "long": "做多(正向)",
        "short": "做空(反向)",
    }

    lines = ["合约马丁格尔策略列表:"]
    for m in data:
        inst_id = m.get("instId", "N/A")
        state = state_map.get(m.get("state", ""), m.get("state", ""))
        direction = direction_map.get(m.get("direction", ""), m.get("direction", ""))
        lever = m.get("lever", "N/A")
        actual_lever = m.get("actualLever", "")
        total_pnl = float(m.get("totalPnl", "0"))
        float_profit = float(m.get("floatProfit", "0"))
        grid_profit = float(m.get("gridProfit", "0"))
        pnl_ratio = float(m.get("pnlRatio", "0")) * 100
        liq_px = m.get("liqPx", "N/A")

        lever_text = f"{lever}x"
        if actual_lever:
            try:
                lever_text = f"{lever}x(实际{float(actual_lever):.2f}x)"
            except ValueError:
                pass

        total_pnl_str = f"+{total_pnl:.2f}" if total_pnl >= 0 else f"{total_pnl:.2f}"
        float_profit_str = f"+{float_profit:.2f}" if float_profit >= 0 else f"{float_profit:.2f}"
        grid_profit_str = f"+{grid_profit:.2f}" if grid_profit >= 0 else f"{grid_profit:.2f}"
        pnl_ratio_str = f"+{pnl_ratio:.2f}%" if pnl_ratio >= 0 else f"{pnl_ratio:.2f}%"

        lines.append(
            f"- {inst_id} ({state}):\n"
            f"  方向: {direction}, 杠杆: {lever_text}\n"
            f"  总盈亏: {total_pnl_str} USDT, 浮动盈亏: {float_profit_str}\n"
            f"  已捕获收益: {grid_profit_str}, 收益率: {pnl_ratio_str}\n"
            f"  爆仓价: {liq_px}"
        )

    return "\n".join(lines)


def query_account_balance() -> str:
    """
    查询账户余额

    Returns:
        格式化的余额信息文本
    """
    account = okx_client.account
    res = account.get_account_balance()

    data = res.get("data", [])
    if not data:
        return "无法获取账户余额"

    balance_data = data[0]
    total_eq = float(balance_data.get("totalEq", 0))

    details = balance_data.get("details", [])
    cash_bal = 0.0
    avail_bal = 0.0
    frozen = 0.0

    for detail in details:
        if detail.get("ccy") == "USDT":
            cash_bal = float(detail.get("cashBal", 0))
            avail_bal = float(detail.get("availBal", 0))
            frozen = float(detail.get("frozenBal", 0))
            break

    return (
        f"账户余额:\n"
        f"总权益: {total_eq:.2f} USDT\n\n"
        f"USDT:\n"
        f"  币种余额: {cash_bal:.2f}\n"
        f"  可用余额: {avail_bal:.2f}\n"
        f"  冻结金额: {frozen:.2f}"
    )


def query_candlesticks(inst_id: str, bar: str = "1H", limit: int = 20) -> str:
    """
    查询K线数据

    Args:
        inst_id: 产品ID，如 BTC-USDT-SWAP
        bar: K线周期，支持 1m/5m/15m/1H/4H/1D/1W/1M
        limit: 返回数量，默认20条

    Returns:
        格式化的K线数据文本
    """
    market = okx_client.market
    res = market.get_candlesticks(instId=inst_id, bar=bar, limit=str(limit))
    data = res.get("data", [])

    if not data:
        return f"无法获取 {inst_id} 的K线数据"

    bar_name_map = {
        "1m": "1分钟",
        "5m": "5分钟",
        "15m": "15分钟",
        "1H": "1小时",
        "4H": "4小时",
        "1D": "1天",
        "1W": "1周",
        "1M": "1月",
    }
    bar_name = bar_name_map.get(bar, bar)

    lines = [f"{inst_id} K线数据 ({bar_name}周期):\n"]
    lines.append("时间|开盘价|最高价|最低价|收盘价|成交量")

    for candle in reversed(data):
        ts = candle[0]
        o = float(candle[1])
        h = float(candle[2])
        l = float(candle[3])
        c = float(candle[4])
        vol = float(candle[5])

        dt = datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d %H:%M")

        lines.append(f"{dt}|{o:>10.4f}|{h:>10.4f}|{l:>10.4f}|{c:>10.4f}|{vol:>12.2f}")

    latest_c = float(data[0][4])
    latest_o = float(data[0][1])
    latest_change = ((latest_c - latest_o) / latest_o) * 100 if latest_o > 0 else 0
    latest_change_str = f"+{latest_change:.2f}%" if latest_change >= 0 else f"{latest_change:.2f}%"
    lines.append(f"\n最新价格: {latest_c:.4f} ({latest_change_str})")

    return "\n".join(lines)
