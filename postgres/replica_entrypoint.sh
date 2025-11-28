#!/bin/bash
set -e

# Wait for primary to be ready
until pg_isready -h postgres_primary -p 5432 -U user
do
  echo "Waiting for primary database..."
  sleep 2
done

# Cleanup data directory
rm -rf /var/lib/postgresql/data/*

# Perform base backup
pg_basebackup -h postgres_primary -D /var/lib/postgresql/data -U replicator -v -P -X stream -R -w

# Start PostgreSQL
exec docker-entrypoint.sh postgres
