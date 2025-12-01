#!/bin/bash
set -e

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '$REPLICATOR_PASSWORD';
EOSQL

# Configure host based authentication
echo "host replication replicator 0.0.0.0/0 trust" >> /var/lib/postgresql/data/pg_hba.conf
