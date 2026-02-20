#!/bin/bash
# GridAIBot 部署脚本
# 适用于 Ubuntu/Debian 系统

set -e

echo "========================================"
echo "  GridAIBot 部署脚本"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
APP_NAME="gridaibot"
APP_DIR="/opt/gridaibot"
APP_USER="gridai"
APP_GROUP="gridai"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 权限运行此脚本${NC}"
    exit 1
fi

# 步骤 1: 安装系统依赖
echo -e "${YELLOW}[1/6] 安装系统依赖...${NC}"
apt update
apt install -y curl git

# 步骤 2: 安装 uv (Python 包管理器)
echo -e "${YELLOW}[2/6] 安装 uv 包管理器...${NC}"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 步骤 3: 创建用户和目录
echo -e "${YELLOW}[3/6] 创建用户和目录...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false "$APP_USER"
fi

mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

# 步骤 4: 复制项目文件
echo -e "${YELLOW}[4/6] 复制项目文件...${NC}"
# 假设脚本在项目目录中运行
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$PROJECT_DIR"/* "$APP_DIR/"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

# 步骤 5: 安装 Python 依赖
echo -e "${YELLOW}[5/6] 安装 Python 依赖...${NC}"
cd "$APP_DIR"
sudo -u "$APP_USER" -E bash -c "cd $APP_DIR && uv sync"

# 步骤 6: 配置 systemd 服务
echo -e "${YELLOW}[6/6] 配置 systemd 服务...${NC}"
cp "$APP_DIR/deploy/gridaibot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable gridaibot

echo ""
echo -e "${GREEN}========================================"
echo "  部署完成!"
echo "========================================${NC}"
echo ""
echo "下一步操作:"
echo "1. 编辑配置文件: nano $APP_DIR/.env"
echo "   (参考 $APP_DIR/.env.example 填写配置)"
echo ""
echo "2. 启动服务: systemctl start gridaibot"
echo "3. 查看状态: systemctl status gridaibot"
echo "4. 查看日志: journalctl -u gridaibot -f"
echo ""
