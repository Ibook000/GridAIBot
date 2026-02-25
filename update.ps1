# GridAIBot 更新脚本
# 使用方法: .\update.ps1 或 .\update.ps1 "提交信息"

param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       GridAIBot 更新脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Git状态
Write-Host "[1/4] 检查Git状态..." -ForegroundColor Yellow
$status = git status --porcelain
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git 命令执行失败" -ForegroundColor Red
    exit 1
}

if ($status.Count -eq 0) {
    Write-Host "没有需要提交的更改" -ForegroundColor Green
    exit 0
}

Write-Host "发现 $($status.Count) 个更改:" -ForegroundColor Green
git status --short

# 获取提交信息
if ($Message -eq "") {
    Write-Host ""
    Write-Host "[2/4] 请输入提交信息 (直接回车使用默认信息):" -ForegroundColor Yellow
    $Message = Read-Host "提交信息 [Update: 代码更新]"
    if ($Message -eq "") {
        $Message = "Update: 代码更新"
    }
}

Write-Host "提交信息: $Message" -ForegroundColor Green

# 添加所有更改
Write-Host ""
Write-Host "[3/4] 暂存所有更改..." -ForegroundColor Yellow
git add -A

if ($LASTEXITCODE -ne 0) {
    Write-Host "git add 失败" -ForegroundColor Red
    exit 1
}

# 提交更改
Write-Host "提交更改..." -ForegroundColor Yellow
git commit -m $Message

if ($LASTEXITCODE -ne 0) {
    Write-Host "git commit 失败" -ForegroundColor Red
    exit 1
}

# 推送到GitHub
Write-Host ""
Write-Host "[4/4] 推送到GitHub..." -ForegroundColor Yellow
git push origin master

if ($LASTEXITCODE -ne 0) {
    Write-Host "git push 失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "       更新成功!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
