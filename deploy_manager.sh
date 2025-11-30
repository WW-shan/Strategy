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
# 假设您的 Replica 服务器是 Swarm Manager
# 如果不是，请修改为 VPS_PRIMARY_IP 或其他
MANAGER_IP="$VPS_REPLICA_IP" 
REMOTE_DIR="/root/strategy"
SSH_USER="${VPS_USER:-root}"
# =====================================

echo "🚀 开始发布到 Manager 节点: $MANAGER_IP"

# 1. 同步配置文件 (docker-stack.yml, .env, deploy目录)
echo "📂 同步配置文件..."
rsync -avz --quiet \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '.DS_Store' \
    ./ "$SSH_USER@$MANAGER_IP:$REMOTE_DIR"

# 2. 远程执行部署命令
echo "🐳 执行 Swarm 部署..."
ssh "$SSH_USER@$MANAGER_IP" "
    cd $REMOTE_DIR && \
    # 加载环境变量
    export \$(cat .env | grep -v '#' | xargs) && \
    
    # 重新部署 Stack (Swarm 会自动拉取新镜像并更新服务)
    docker stack deploy -c docker-stack.yml strategy_cluster && \
    
    # 强制更新服务以拉取 latest 镜像 (解决 Swarm 不自动拉取 latest 的问题)
    docker service update --image wwshan/strategy-admin:latest strategy_cluster_admin_service --force --quiet && \
    docker service update --image wwshan/strategy-bot:latest strategy_cluster_bot_service --force --quiet && \
    docker service update --image wwshan/strategy-engine:latest strategy_cluster_strategy_engine --force --quiet
"

echo "✅ 发布完成！服务正在后台滚动更新。"
