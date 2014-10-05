ALTER TABLE pools ADD COLUMN credit_limit numeric NOT NULL default 20;
ALTER TABLE pools_history ADD COLUMN credit_limit numeric NOT NULL default 20;
