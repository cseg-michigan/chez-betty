#!/usr/bin/env sh

set -e

echo "drop database betty" | psql
ssh chezbetty.store 'pg_dump chezbetty | gzip > betty_dump.psql.gz'
scp chezbetty.store:betty_dump.psql.gz .
ssh chezbetty.store 'rm betty_dump.psql.gz'
gunzip betty_dump.psql.gz
echo 'create database betty' | psql
psql betty < betty_dump.psql
rm betty_dump.psql

