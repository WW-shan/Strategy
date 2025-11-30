#!/bin/bash

# 确保脚本在错误时停止
set -e

echo "🔗 开始创建 .env 软链接..."

# 定义需要创建链接的子目录列表
DIRS=(
    "deploy/vps_app"
    "deploy/vps_primary"
    "deploy/vps_replica"
    "deploy/vps_strategy"
)

# 获取脚本所在的根目录 (假设脚本在根目录运行)
ROOT_DIR=$(pwd)

# 检查根目录是否存在 .env，如果不存在则从 .env.example 复制
if [ ! -f "$ROOT_DIR/.env" ]; then
    if [ -f "$ROOT_DIR/.env.example" ]; then
        echo "📄 未找到 .env，正在从 .env.example 创建..."
        cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
        echo "✅ .env 创建成功"
    else
        echo "❌ 错误：未找到 .env.example 模板文件，无法创建 .env"
        exit 1
    fi
else
    echo "ℹ️  已存在 .env 文件，跳过创建"
fi

for dir in "${DIRS[@]}"; do
    TARGET_DIR="$ROOT_DIR/$dir"
    
    # 检查目录是否存在
    if [ -d "$TARGET_DIR" ]; then
        echo "正在处理: $dir"
        
        # 进入目标目录
        cd "$TARGET_DIR"
        
        # 如果已存在 .env 文件或链接，先删除以避免冲突
        if [ -e ".env" ] || [ -L ".env" ]; then
            echo "  ⚠️  发现旧的 .env，正在移除..."
            rm .env
        fi
        
        # 创建指向根目录 .env 的软链接
        # ../../.env 表示向上两级找到根目录的 .env
        # 尝试创建软链接 (Windows Git Bash 可能会创建副本)
        ln -s ../../.env .env
        
        if [ -L ".env" ]; then
            echo "  ✅ 软链接创建成功"
        elif [ -f ".env" ]; then
            echo "  ⚠️  Windows提示: 已创建文件副本 (非软链接)"
            echo "      注意: 修改根目录 .env 后，请重新运行此脚本以同步更改"
        else
            echo "  ❌ 创建失败"
        fi
        
        # 返回根目录
        cd "$ROOT_DIR"
    else
        echo "❌ 目录不存在: $dir"
    fi
done

echo "🎉 所有操作完成！"
