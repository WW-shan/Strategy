#!/bin/bash

# 确保脚本在错误时停止
set -e

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
else
    echo "❌ 未找到 .env 文件"
    exit 1
fi

# =================配置=================
# 本脚本设计为直接在 Manager 节点上运行
# =====================================

echo "🚀 开始在本地 Manager 节点执行部署..."

# 1. 重新部署 Stack (Swarm 会自动拉取新镜像并更新服务)
echo "🐳 执行 Swarm 部署..."
docker stack deploy -c docker-stack.yml strategy_cluster

# 2. 强制更新服务以拉取 latest 镜像 (解决 Swarm 不自动拉取 latest 的问题)
echo "🔄 强制更新服务镜像..."
docker service update --image wwshan/strategy-admin:latest strategy_cluster_admin_service --force --quiet
docker service update --image wwshan/strategy-bot:latest strategy_cluster_bot_service --force --quiet
docker service update --image wwshan/strategy-engine:latest strategy_cluster_strategy_engine --force --quiet

echo "✅ 发布完成！服务正在后台滚动更新。"
