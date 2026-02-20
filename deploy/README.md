# GridAIBot 服务器部署指南

本文档介绍如何将 GridAIBot 部署到 Linux 服务器。

## 目录结构

```
deploy/
├── gridaibot.service    # systemd 服务配置
├── install.sh           # 自动安装脚本
└── README.md           # 本文档
```

## 前置要求

- Linux 服务器 (Ubuntu 20.04+ / Debian 11+ 推荐)
- root 或 sudo 权限
- 网络连接正常

## 快速部署

### 方法一: 使用自动安装脚本

1. 将项目上传到服务器:
```bash
# 使用 scp
scp -r /path/to/GridAIBot user@server:/tmp/

# 或使用 rsync
rsync -avz /path/to/GridAIBot user@server:/tmp/
```

2. 在服务器上运行安装脚本:
```bash
cd /tmp/GridAIBot
chmod +x deploy/install.sh
sudo ./deploy/install.sh
```

3. 配置环境变量:
```bash
sudo nano /opt/gridaibot/.env
```

4. 启动服务:
```bash
sudo systemctl start gridaibot
sudo systemctl status gridaibot
```

### 方法二: 手动部署

#### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y curl git
```

#### 2. 安装 uv 包管理器

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
```

#### 3. 创建应用目录和用户

```bash
sudo useradd -r -s /bin/false gridai
sudo mkdir -p /opt/gridaibot
```

#### 4. 上传项目文件

```bash
# 在本地机器上
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
    /path/to/GridAIBot/ user@server:/opt/gridaibot/
```

#### 5. 设置权限

```bash
sudo chown -R gridai:gridai /opt/gridaibot
```

#### 6. 安装 Python 依赖

```bash
cd /opt/gridaibot
sudo -u gridai uv sync
```

#### 7. 配置环境变量

```bash
sudo nano /opt/gridaibot/.env
```

填入以下内容:
```env
# Discord Bot 配置
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# OKX API 配置
OKX_API_KEY=your_okx_api_key_here
OKX_API_SECRET=your_okx_api_secret_here
OKX_PASSPHRASE=your_okx_passphrase_here
OKX_BASE_URL=https://www.okx.com
OKX_FLAG=0

# LLM 配置
LLM_BASE_URL=https://apis.iflow.cn/v1
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=qwen3-max
```

#### 8. 配置 systemd 服务

```bash
sudo cp /opt/gridaibot/deploy/gridaibot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gridaibot
sudo systemctl start gridaibot
```

## 服务管理命令

```bash
# 启动服务
sudo systemctl start gridaibot

# 停止服务
sudo systemctl stop gridaibot

# 重启服务
sudo systemctl restart gridaibot

# 查看状态
sudo systemctl status gridaibot

# 查看实时日志
sudo journalctl -u gridaibot -f

# 查看最近 100 行日志
sudo journalctl -u gridaibot -n 100
```

## 更新部署

当需要更新代码时:

```bash
# 1. 停止服务
sudo systemctl stop gridaibot

# 2. 上传新代码
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
    /path/to/GridAIBot/ user@server:/opt/gridaibot/

# 3. 更新依赖 (如有变化)
cd /opt/gridaibot
sudo -u gridai uv sync

# 4. 重启服务
sudo systemctl start gridaibot
```

## 故障排查

### 检查服务状态
```bash
sudo systemctl status graidaibot
```

### 查看错误日志
```bash
sudo journalctl -u gridaibot -n 50 --no-pager
```

### 检查配置文件
```bash
cat /opt/gridaibot/.env
```

### 手动测试运行
```bash
cd /opt/gridaibot
sudo -u gridai -E bash -c "source .venv/bin/activate && python discord_bot.py"
```

## 安全建议

1. 确保 `.env` 文件权限正确:
```bash
sudo chmod 600 /opt/gridaibot/.env
sudo chown gridai:gridai /opt/gridaibot/.env
```

2. 配置防火墙 (如需要):
```bash
sudo ufw allow ssh
sudo ufw enable
```

3. 定期备份 `.env` 配置文件

## 文件位置说明

| 文件/目录 | 位置 |
|----------|------|
| 应用目录 | `/opt/gridaibot` |
| 环境配置 | `/opt/gridaibot/.env` |
| 服务配置 | `/etc/systemd/system/gridaibot.service` |
| 日志 | 通过 `journalctl` 查看 |
