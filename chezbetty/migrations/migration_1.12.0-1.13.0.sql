ALTER TABLE accounts ADD COLUMN archived_balance NUMERIC;
ALTER TABLE users ADD COLUMN archived BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE accounts_history ADD COLUMN archived_balance NUMERIC;
ALTER TABLE users_history ADD COLUMN archived BOOLEAN NOT NULL DEFAULT false;