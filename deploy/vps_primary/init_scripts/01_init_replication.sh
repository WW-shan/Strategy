#!/bin/bash
set -e

echo "初始化 replication 用户和 pg_hba.conf..."

# Create replication user (如果不存在)
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
            CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '$REPLICATOR_PASSWORD';
            RAISE NOTICE 'replicator 用户已创建';
        ELSE
            RAISE NOTICE 'replicator 用户已存在';
        END IF;
    END \$\$;
EOSQL

# 配置 pg_hba.conf
PG_HBA="/var/lib/postgresql/data/pg_hba.conf"

# 清除默认的不安全规则
sed -i '/^host.*all.*all.*0.0.0.0\/0/d' "$PG_HBA"
sed -i '/^host.*all.*all.*::\/0/d' "$PG_HBA"

# 添加安全的白名单规则
cat >> "$PG_HBA" <<EOF

# Docker 内部网络
host    replication     replicator      10.0.0.0/8              scram-sha-256
host    all             all             10.0.0.0/8              scram-sha-256
host    replication     replicator      172.16.0.0/12           scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
EOF

# 仅当提供了合法 IPv4 地址时才追加白名单，避免占位符污染 pg_hba.conf
append_ip_rule() {
    local ip="$1"
    local rule="$2"

    # 粗略校验 IPv4（避免 x.x.x.x 这类占位符）
    if [[ -n "$ip" && "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        echo "$rule" >> "$PG_HBA"
    else
        echo "跳过无效 IP: '$ip'" >&2
    fi
}

# 添加 VPS IP 白名单（仅在 IP 合法时）
append_ip_rule "$VPS_REPLICA_IP" "host    replication     replicator      $VPS_REPLICA_IP/32      scram-sha-256"
append_ip_rule "$VPS_REPLICA_IP" "host    all             all             $VPS_REPLICA_IP/32      scram-sha-256"
append_ip_rule "$VPS_APP_IP"     "host    all             all             $VPS_APP_IP/32              scram-sha-256"
append_ip_rule "$VPS_STRATEGY_IP" "host    all             all             $VPS_STRATEGY_IP/32         scram-sha-256"

# 拒绝所有其他连接
echo "host    all             all             0.0.0.0/0                   reject" >> "$PG_HBA"

echo "初始化完成"
