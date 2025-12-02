#!/bin/bash
set -e

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '$REPLICATOR_PASSWORD';
EOSQL

# Configure host based authentication with RESTRICTIVE rules
# Remove the default trust rules for external connections
sed -i '/host.*all.*all.*0.0.0.0\/0/d' /var/lib/postgresql/data/pg_hba.conf
sed -i '/host.*all.*all.*::\/0/d' /var/lib/postgresql/data/pg_hba.conf

# 白名单策略 - 只允许集群内的服务器访问
# 1. Docker 内部网络
echo "host replication replicator 10.0.0.0/8 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
echo "host all all 10.0.0.0/8 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf

# 2. 允许本机访问(主库自己)
echo "host all all 127.0.0.1/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf

# 注意: 下面需要在 docker-stack.yml 中传入环境变量
# VPS_PRIMARY_IP, VPS_APP_IP, VPS_REPLICA_IP, VPS_STRATEGY_IP

# 3. 允许从库服务器 (使用环境变量,在运行时替换)
if [ ! -z "$VPS_REPLICA_IP" ]; then
    echo "host replication replicator $VPS_REPLICA_IP/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
    echo "host all all $VPS_REPLICA_IP/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
fi

# 4. 允许应用服务器
if [ ! -z "$VPS_APP_IP" ]; then
    echo "host all all $VPS_APP_IP/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
fi

# 5. 允许策略服务器
if [ ! -z "$VPS_STRATEGY_IP" ]; then
    echo "host all all $VPS_STRATEGY_IP/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
fi

# 6. 拒绝所有其他IP (阻止攻击者)
echo "host all all 0.0.0.0/0 reject" >> /var/lib/postgresql/data/pg_hba.conf
