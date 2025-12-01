#!/bin/bash
set -e

# CONFIGURATION
echo "Waiting for primary database at $PRIMARY_HOST..."

# Debug: Check TCP connectivity using bash /dev/tcp
echo "Debug: Checking TCP port 5432 on $PRIMARY_HOST..."
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$PRIMARY_HOST/5432" 2>/dev/null; then
    echo "Debug: TCP connection to $PRIMARY_HOST:5432 successful"
else
    echo "Debug: TCP connection to $PRIMARY_HOST:5432 FAILED"
    echo "Debug: This usually indicates a Firewall/Security Group issue blocking port 5432 or Overlay network ports (UDP 4789)."
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
