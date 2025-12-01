#!/bin/bash
set -e

# CONFIGURATION
echo "Waiting for primary database at $PRIMARY_HOST..."

# Debug: Install netcat for TCP testing
echo "Debug: Installing netcat..."
apk add --no-cache netcat-openbsd

# Debug: Check network connectivity
echo "Debug: Checking network connectivity to $PRIMARY_HOST..."
PING_OUTPUT=$(ping -c 2 "$PRIMARY_HOST" 2>&1)
if [ $? -eq 0 ]; then
    echo "Debug: Ping to $PRIMARY_HOST successful"
    echo "Debug: Ping output: $PING_OUTPUT"
else
    echo "Debug: Ping to $PRIMARY_HOST failed"
    echo "Debug: Ping output: $PING_OUTPUT"
fi

# Debug: Check TCP connectivity
echo "Debug: Checking TCP port 5432 on $PRIMARY_HOST..."
if nc -zv -w 5 "$PRIMARY_HOST" 5432; then
    echo "Debug: TCP connection to $PRIMARY_HOST:5432 successful"
else
    echo "Debug: TCP connection to $PRIMARY_HOST:5432 FAILED"
fi

until pg_isready -h "$PRIMARY_HOST" -p 5432 -U replicator
do
  echo "Waiting for primary database... (pg_isready returned $?)"
  sleep 2
done

echo "Cleaning up data directory..."
rm -rf /var/lib/postgresql/data/*

echo "Starting Base Backup from $PRIMARY_HOST..."
pg_basebackup -h $PRIMARY_HOST -p 5432 -D /var/lib/postgresql/data -U replicator -v -P -X stream -R -w

echo "Backup complete. Starting PostgreSQL as Replica..."
exec docker-entrypoint.sh postgres
