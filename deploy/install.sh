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
fi

# 确保 uv 在 PATH 中
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv &> /dev/null; then
    echo -e "${RED}uv 安装失败，请手动安装${NC}"
    exit 1
fi

echo -e "${GREEN}uv 已安装: $(which uv)${NC}"

# 步骤 3: 创建用户和目录
echo -e "${YELLOW}[3/6] 创建用户和目录...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false "$APP_USER"
fi

mkdir -p "$APP_DIR"

# 步骤 4: 复制项目文件
echo -e "${YELLOW}[4/6] 复制项目文件...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$PROJECT_DIR"/* "$APP_DIR/"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

# 步骤 5: 安装 Python 依赖
echo -e "${YELLOW}[5/6] 安装 Python 依赖...${NC}"
cd "$APP_DIR"

# 使用 root 用户安装依赖（uv 会创建 .venv 目录）
uv sync

# 设置权限
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

# 验证虚拟环境
if [ ! -f "$APP_DIR/.venv/bin/python" ]; then
    echo -e "${RED}虚拟环境创建失败${NC}"
    exit 1
fi

echo -e "${GREEN}Python 虚拟环境已创建: $APP_DIR/.venv/bin/python${NC}"

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
