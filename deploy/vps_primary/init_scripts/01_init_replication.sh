#!/bin/bash
set -e

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '$PGPASSWORD';
EOSQL

# Configure host based authentication
# ALLOW REPLICA IP HERE! Replace 0.0.0.0/0 with specific IP for security
echo "host replication replicator 0.0.0.0/0 trust" >> /var/lib/postgresql/data/pg_hba.conf
