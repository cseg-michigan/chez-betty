ALTER TABLE pools ADD COLUMN credit_limit numeric NOT NULL default 20;
ALTER TABLE pools_history ADD COLUMN credit_limit numeric NOT NULL default 20;
ALTER TABLE box_items ADD COLUMN percentage numeric NOT NULL default 0;

ALTER TABLE transactions ADD COLUMN discount NUMERIC;
