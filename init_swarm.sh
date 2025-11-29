#!/bin/bash

# 确保脚本在错误时停止
set -e

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
else
    echo "❌ 错误：未找到 .env 文件"
    exit 1
fi

SSH_USER="${VPS_USER:-root}"
MANAGER_IP="$VPS_REPLICA_IP"

if [ -z "$MANAGER_IP" ] || [ "$MANAGER_IP" == "x.x.x.x" ]; then
    echo "❌ 错误：VPS_REPLICA_IP 未在 .env 中配置，无法确定 Manager 节点。"
    exit 1
fi

echo "🚀 开始初始化 Swarm 集群..."
echo "   👑 Manager 节点: $MANAGER_IP (Replica VPS)"
echo "   👤 SSH 用户: $SSH_USER"

# ==========================================
# 1. 初始化 Manager 节点
# ==========================================
echo "---------------------------------------------------"
echo "🔵 正在配置 Manager..."
ssh "$SSH_USER@$MANAGER_IP" "
    # 检查是否已经是 Swarm 模式
    if ! docker info | grep -q 'Swarm: active'; then
        echo '   执行 swarm init...'
        docker swarm init --advertise-addr $MANAGER_IP
    else
        echo '   Swarm 已经在运行中。'
    fi
"

# 获取 Worker 加入令牌
WORKER_TOKEN=$(ssh "$SSH_USER@$MANAGER_IP" "docker swarm join-token worker -q")
echo "   🔑 Worker Token: $WORKER_TOKEN"

# 给 Manager 节点打标签 (role=replica_db)
MANAGER_ID=$(ssh "$SSH_USER@$MANAGER_IP" "docker info -f '{{.Swarm.NodeID}}'")
echo "   🏷️  正在给 Manager ($MANAGER_ID) 打标签: role=replica_db"
ssh "$SSH_USER@$MANAGER_IP" "docker node update --label-add role=replica_db $MANAGER_ID"

# ==========================================
# 2. 定义添加 Worker 的函数
# ==========================================
add_worker() {
    local NODE_IP=$1
    local ROLE=$2
    local NAME=$3

    if [ -z "$NODE_IP" ] || [ "$NODE_IP" == "x.x.x.x" ]; then
        echo "⚠️  跳过 $NAME: IP 未配置。"
        return
    fi

    echo "---------------------------------------------------"
    echo "🔵 正在添加 Worker: $NAME ($NODE_IP)"
    
    # 1. 远程执行加入命令
    ssh "$SSH_USER@$NODE_IP" "
        # 如果已经在 Swarm 里，先强制退出 (防止冲突)
        if docker info | grep -q 'Swarm: active'; then
            echo '   ⚠️  检测到旧的 Swarm 配置，正在清理...'
            docker swarm leave --force
        fi
        
        echo '   🔗 加入 Swarm 集群...'
        docker swarm join --token $WORKER_TOKEN $MANAGER_IP:2377
    "

    # 2. 获取该节点的 Node ID (需要在节点上执行)
    NODE_ID=$(ssh "$SSH_USER@$NODE_IP" "docker info -f '{{.Swarm.NodeID}}'")
    echo "   🆔 Node ID: $NODE_ID"

    # 3. 在 Manager 上给该节点打标签
    echo "   🏷️  应用标签: role=$ROLE"
    ssh "$SSH_USER@$MANAGER_IP" "docker node update --label-add role=$ROLE $NODE_ID"
    
    echo "   ✅ 添加成功！"
}

# ==========================================
# 3. 添加所有节点
# ==========================================
add_worker "$VPS_APP_IP"      "app"        "应用服务器 (App)"
add_worker "$VPS_PRIMARY_IP"  "primary_db" "主数据库 (Primary)"
add_worker "$VPS_STRATEGY_IP" "strategy"   "策略引擎 (Strategy)"

echo "---------------------------------------------------"
echo "🎉 集群初始化完成！"
echo "📊 当前节点状态:"
ssh "$SSH_USER@$MANAGER_IP" "docker node ls"
