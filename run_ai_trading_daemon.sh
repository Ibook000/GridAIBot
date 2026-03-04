#!/bin/bash
# AI 交易分析脚本 - 24小时守护进程版
# 用法: 
#   ./run_ai_trading_daemon.sh start  - 启动守护进程
#   ./run_ai_trading_daemon.sh stop   - 停止守护进程
#   ./run_ai_trading_daemon.sh status - 查看状态
#   ./run_ai_trading_daemon.sh restart - 重启

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 进程PID文件
PID_FILE="/tmp/ai_trading_daemon.pid"
LOG_FILE="webhook/trading_analysis/daemon.log"

# 激活虚拟环境
activate_venv() {
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "../.venv" ]; then
        source ../.venv/bin/activate
    fi
}

# 启动守护进程
start_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "进程已在运行中 (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "启动 AI 交易分析守护进程..."
    
    # 确保日志目录存在
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 后台运行
    activate_venv
    nohup python webhook/ai_trading.py >> "$LOG_FILE" 2>&1 &
    
    echo $! > "$PID_FILE"
    echo "守护进程已启动 (PID: $(cat $PID_FILE))"
    echo "日志文件: $LOG_FILE"
}

# 停止守护进程
stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "停止守护进程 (PID: $PID)..."
            kill "$PID"
            rm -f "$PID_FILE"
            echo "已停止"
        else
            echo "进程未运行"
            rm -f "$PID_FILE"
        fi
    else
        echo "未找到PID文件，尝试查找进程..."
        PIDS=$(pgrep -f "ai_trading.py")
        if [ -n "$PIDS" ]; then
            echo "找到运行中的进程: $PIDS"
            kill $PIDS
            echo "已停止"
        else
            echo "未找到运行中的进程"
        fi
    fi
}

# 查看状态
status_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "守护进程运行中 (PID: $PID)"
            
            # 显示最近日志
            if [ -f "$LOG_FILE" ]; then
                echo ""
                echo "=== 最近日志 ==="
                tail -n 20 "$LOG_FILE"
            fi
        else
            echo "PID文件存在但进程未运行"
            rm -f "$PID_FILE"
        fi
    else
        echo "守护进程未运行"
        # 检查是否有其他实例
        PIDS=$(pgrep -f "ai_trading.py")
        if [ -n "$PIDS" ]; then
            echo "发现运行中的进程: $PIDS"
        fi
    fi
}

# 重启
restart_daemon() {
    stop_daemon
    sleep 2
    start_daemon
}

# 根据参数执行
case "$1" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    status)
        status_daemon
        ;;
    restart)
        restart_daemon
        ;;
    *)
        echo "用法: $0 {start|stop|status|restart}"
        echo ""
        echo "示例:"
        echo "  $0 start    # 启动守护进程"
        echo "  $0 stop     # 停止守护进程"
        echo "  $0 status   # 查看运行状态"
        echo "  $0 restart  # 重启守护进程"
        exit 1
        ;;
esac
