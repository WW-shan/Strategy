#!/bin/bash
set -e

# CONFIGURATION
echo "Waiting for primary database at $PRIMARY_HOST..."

# Debug: Check network connectivity
echo "Debug: Checking network connectivity to $PRIMARY_HOST..."
if ping -c 2 "$PRIMARY_HOST" > /dev/null 2>&1; then
    echo "Debug: Ping to $PRIMARY_HOST successful"
else
    echo "Debug: Ping to $PRIMARY_HOST failed"
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
