#!/usr/bin/sh

set -e

echo "drop database betty" | psql
ssh chezbetty.eecs.umich.edu 'pg_dump chezbetty | gzip > betty_dump.psql.gz'
scp chezbetty.eecs.umich.edu:betty_dump.psql.gz .
ssh chezbetty.eecs.umich.edu 'rm betty_dump.psql.gz'
gunzip betty_dump.psql.gz
echo 'create database betty' | psql
psql betty < betty_dump.psql
rm betty_dump.psql

