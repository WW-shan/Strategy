#!/bin/bash
set -e

# CONFIGURATION
echo "Waiting for primary database at $PRIMARY_HOST..."

until pg_isready -h "$PRIMARY_HOST" -p 5432 -U replicator
do
  echo "Waiting for primary database..."
  sleep 2
done

echo "Cleaning up data directory..."
rm -rf /var/lib/postgresql/data/*

echo "Starting Base Backup from $PRIMARY_HOST..."
PGPASSWORD="$PGPASSWORD" pg_basebackup -h "$PRIMARY_HOST" -p 5432 -D /var/lib/postgresql/data -U replicator -v -P -X stream -R -w

echo "Backup complete. Starting PostgreSQL as Replica..."
exec docker-entrypoint.sh postgres
