#!/bin/bash

# 确保脚本在错误时停止
set -e

# 硬编码 Docker 用户名
DOCKER_USERNAME="wwshan"

echo "🐳 正在登录 Docker Hub..."
# 如果您已经登录过，可以注释掉下面这行，或者保留它以确保登录状态
docker login

build_and_push() {
    local SERVICE_NAME=$1
    local IMAGE_NAME="$DOCKER_USERNAME/$SERVICE_NAME:latest"
    local BUILD_DIR=$2

    echo "---------------------------------------------------"
    echo "🔨 构建镜像: $IMAGE_NAME"
    # 使用 --platform linux/amd64 确保在 VPS 上能运行 (如果您的开发机是 M1/M2 Mac)
    docker build --platform linux/amd64 -t "$IMAGE_NAME" "$BUILD_DIR"

    echo "⬆️  推送镜像: $IMAGE_NAME"
    docker push "$IMAGE_NAME"
    echo "✅ 完成: $SERVICE_NAME"
}

echo "🚀 开始构建并推送镜像..."

build_and_push "strategy-admin"   "./services/admin"
build_and_push "strategy-bot"     "./services/bot"
build_and_push "strategy-engine"  "./services/strategy_engine"

echo "---------------------------------------------------"
echo "🎉 所有镜像已推送到 Docker Hub！"
echo "👉 现在您可以在 Manager 节点上运行: docker stack deploy -c docker-stack.yml strategy_cluster"
