#!/bin/bash
set -e

# 定义 pg_hba.conf 配置函数
configure_pg_hba() {
    local PG_HBA="$PGDATA/pg_hba.conf"
    
    cat > "$PG_HBA" <<EOF
# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# 本地连接
local   all             all                                     trust
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256

# Docker 内部网络
host    replication     replicator      10.0.0.0/8              scram-sha-256
host    all             all             10.0.0.0/8              scram-sha-256
host    replication     replicator      172.16.0.0/12           scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
EOF

    # 添加 VPS IP 白名单
    [ ! -z "$VPS_REPLICA_IP" ] && cat >> "$PG_HBA" <<EOF
host    replication     replicator      $VPS_REPLICA_IP/32      scram-sha-256
host    all             all             $VPS_REPLICA_IP/32      scram-sha-256
EOF

    [ ! -z "$VPS_APP_IP" ] && echo "host    all             all             $VPS_APP_IP/32              scram-sha-256" >> "$PG_HBA"
    [ ! -z "$VPS_STRATEGY_IP" ] && echo "host    all             all             $VPS_STRATEGY_IP/32         scram-sha-256" >> "$PG_HBA"
    echo "host    all             all             0.0.0.0/0                   reject" >> "$PG_HBA"
}

# 检查数据目录是否已初始化
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "数据目录为空，使用标准初始化流程（init 脚本会创建用户）..."
    # 使用 exec 直接替换当前进程，让 docker-entrypoint.sh 成为主进程
    exec docker-entrypoint.sh postgres "$@"
fi

echo "数据目录已存在，配置 pg_hba.conf..."
configure_pg_hba
echo "pg_hba.conf 配置完成"

# 后台启动 PostgreSQL
postgres "$@" &
PG_PID=$!

# 等待就绪
echo "等待 PostgreSQL 启动..."
for i in {1..30}; do
    if pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
        echo "PostgreSQL 已就绪"
        break
    fi
    sleep 1
done

# 确保数据库存在
echo "检查数据库 $POSTGRES_DB..."
DB_EXISTS=$(psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'" 2>/dev/null || echo "0")
if [ "$DB_EXISTS" != "1" ]; then
    echo "创建数据库 $POSTGRES_DB..."
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB" || echo "数据库创建失败（可能已存在）"
else
    echo "数据库已存在"
fi

# 确保 replicator 用户存在
echo "检查 replicator 用户..."
USER_EXISTS=$(psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='replicator'" 2>/dev/null || echo "0")
if [ "$USER_EXISTS" != "1" ]; then
    echo "创建 replicator 用户..."
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '$REPLICATOR_PASSWORD'" || echo "用户创建失败（可能已存在）"
else
    echo "replicator 用户已存在"
fi

echo "初始化检查完成，PostgreSQL 继续运行"

# 保持前台运行
wait $PG_PID
