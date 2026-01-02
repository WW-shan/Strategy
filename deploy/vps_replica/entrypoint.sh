#!/bin/bash
set -e

# CONFIGURATION
echo "Attempting to connect to primary database..."

# 尝试内网连接（Swarm Overlay）
INTERNAL_HOST="postgres_primary"
EXTERNAL_HOST="${PRIMARY_HOST_FALLBACK:-}"

echo "Step 1: Testing internal connection to $INTERNAL_HOST..."
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$INTERNAL_HOST/5432" 2>/dev/null; then
    echo "✓ Internal connection successful. Using Overlay network."
    PRIMARY_HOST="$INTERNAL_HOST"
else
    echo "✗ Internal connection failed."
    if [ -n "$EXTERNAL_HOST" ]; then
        echo "Step 2: Testing fallback connection to $EXTERNAL_HOST..."
        if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$EXTERNAL_HOST/5432" 2>/dev/null; then
            echo "✓ Fallback connection successful. Using public IP."
            PRIMARY_HOST="$EXTERNAL_HOST"
        else
            echo "✗ Both internal and external connections failed. Retrying internal..."
            PRIMARY_HOST="$INTERNAL_HOST"
        fi
    else
        echo "⚠ No fallback IP configured. Will retry internal connection."
        PRIMARY_HOST="$INTERNAL_HOST"
    fi
fi

echo "Using PRIMARY_HOST=$PRIMARY_HOST"

# 检查数据目录是否已初始化
if [ -s "/var/lib/postgresql/data/PG_VERSION" ]; then
    echo "=== Replica already initialized ==="
    echo "Data directory exists, skipping base backup"
    echo "Starting PostgreSQL as Replica..."
    exec docker-entrypoint.sh postgres -c hot_standby=on
fi

echo "=== Initializing new replica ==="

until pg_isready -h "$PRIMARY_HOST" -p 5432 -U replicator
do
  echo "Waiting for primary database... (pg_isready returned $?)"
  sleep 2
done

echo "Cleaning up data directory..."
rm -rf /var/lib/postgresql/data/*

echo "Starting Base Backup from $PRIMARY_HOST..."
pg_basebackup -h $PRIMARY_HOST -p 5432 -D /var/lib/postgresql/data -U replicator -v -P -X stream -R

echo "Backup complete. Starting PostgreSQL as Replica..."
exec docker-entrypoint.sh postgres -c hot_standby=on
