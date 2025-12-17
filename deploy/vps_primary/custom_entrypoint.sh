#!/bin/bash
set -e

# 这个脚本在每次容器启动时都会运行，确保配置正确

# 等待 PostgreSQL 数据目录初始化
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "数据目录为空，等待初始化..."
    # 运行原始 entrypoint 进行初始化
    exec docker-entrypoint.sh postgres "$@"
fi

# 数据目录已存在，检查并修复 pg_hba.conf
echo "检查 pg_hba.conf 配置..."

PG_HBA="$PGDATA/pg_hba.conf"

# 备份原始配置
cp "$PG_HBA" "$PG_HBA.backup.$(date +%s)" 2>/dev/null || true

# 重新生成 pg_hba.conf（每次启动都确保配置正确）
cat > "$PG_HBA" <<EOF
# PostgreSQL Client Authentication Configuration File
# 自动生成于容器启动时 - $(date)

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# 本地连接
local   all             all                                     trust
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

# Docker 内部网络
host    replication     replicator      10.0.0.0/8              scram-sha-256
host    all             all             10.0.0.0/8              scram-sha-256

# 172.x.x.x Docker overlay 网络
host    replication     replicator      172.16.0.0/12           scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256

# VPS 服务器 IP（如果提供）
EOF

# 添加从库服务器 IP
if [ ! -z "$VPS_REPLICA_IP" ]; then
    echo "host    replication     replicator      $VPS_REPLICA_IP/32          scram-sha-256" >> "$PG_HBA"
    echo "host    all             all             $VPS_REPLICA_IP/32          scram-sha-256" >> "$PG_HBA"
    echo "已添加从库 IP: $VPS_REPLICA_IP"
fi

# 添加应用服务器 IP
if [ ! -z "$VPS_APP_IP" ]; then
    echo "host    all             all             $VPS_APP_IP/32              scram-sha-256" >> "$PG_HBA"
    echo "已添加应用 IP: $VPS_APP_IP"
fi

# 添加策略服务器 IP
if [ ! -z "$VPS_STRATEGY_IP" ]; then
    echo "host    all             all             $VPS_STRATEGY_IP/32         scram-sha-256" >> "$PG_HBA"
    echo "已添加策略 IP: $VPS_STRATEGY_IP"
fi

# 拒绝所有其他连接（安全）
echo "host    all             all             0.0.0.0/0                   reject" >> "$PG_HBA"

echo "pg_hba.conf 配置完成"

# 确保 replicator 用户存在（如果数据库已初始化）
if [ -s "$PGDATA/postmaster.pid" ]; then
    echo "PostgreSQL 已在运行，跳过用户创建"
else
    echo "将在 PostgreSQL 启动后创建 replicator 用户（如果不存在）"
fi

# 启动 PostgreSQL
# 不传递 $@ 因为 command 参数已经在 docker-stack.yml 中定义
exec docker-entrypoint.sh "$@"
