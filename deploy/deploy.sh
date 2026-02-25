#!/bin/bash
# GridAIBot 服务器部署脚本
# 用途: 从GitHub仓库拉取最新代码并重启服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
BOT_DIR="/opt/gridaibot"
SERVICE_NAME="gridaibot"
GIT_REPO="https://github.com/Ibook000/GridAIBot.git"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}       GridAIBot 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用root用户运行此脚本${NC}"
    exit 1
fi

# 检查目录是否存在
if [ ! -d "$BOT_DIR" ]; then
    echo -e "${YELLOW}目录 $BOT_DIR 不存在，正在创建...${NC}"
    mkdir -p "$BOT_DIR"
    cd "$BOT_DIR"
    echo -e "${YELLOW}正在克隆仓库...${NC}"
    git clone "$GIT_REPO" .
else
    cd "$BOT_DIR"
fi

# 停止服务
echo ""
echo -e "${YELLOW}[1/4] 停止服务...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    systemctl stop $SERVICE_NAME
    echo -e "${GREEN}服务已停止${NC}"
else
    echo -e "${YELLOW}服务未在运行${NC}"
fi

# 拉取最新代码
echo ""
echo -e "${YELLOW}[2/4] 拉取最新代码...${NC}"
git fetch origin
git pull origin master
echo -e "${GREEN}代码已更新${NC}"

# 安装/更新依赖
echo ""
echo -e "${YELLOW}[3/4] 安装依赖...${NC}"
if [ -f "pyproject.toml" ]; then
    # 检查uv是否可用
    if command -v uv &> /dev/null; then
        uv sync
        echo -e "${GREEN}依赖已更新 (uv)${NC}"
    elif command -v pip &> /dev/null; then
        # 使用pip作为备选方案
        pip install -r requirements.txt 2>/dev/null || pip install -e . 2>/dev/null || echo -e "${YELLOW}未找到依赖文件，跳过${NC}"
        echo -e "${GREEN}依赖已更新 (pip)${NC}"
    else
        echo -e "${RED}未找到 uv 或 pip，无法安装依赖${NC}"
    fi
else
    echo -e "${YELLOW}未找到 pyproject.toml，跳过依赖安装${NC}"
fi

# 重启服务
echo ""
echo -e "${YELLOW}[4/4] 启动服务...${NC}"
systemctl daemon-reload
systemctl start $SERVICE_NAME
sleep 2

# 检查服务状态
if systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}       部署成功!${NC}"
    echo -e "${GREEN}========================================${NC}"
    systemctl status $SERVICE_NAME --no-pager
else
    echo -e "${RED}服务启动失败，请检查日志:${NC}"
    journalctl -u $SERVICE_NAME --no-pager -n 20
    exit 1
fi
