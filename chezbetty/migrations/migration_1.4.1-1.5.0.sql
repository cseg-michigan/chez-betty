ALTER TABLE items ADD COLUMN sales_tax BOOLEAN NOT NULL default FALSE;
ALTER TABLE items ADD COLUMN bottle_dep BOOLEAN NOT NULL default FALSE;
ALTER TABLE boxes ADD COLUMN sales_tax BOOLEAN NOT NULL default FALSE;
ALTER TABLE boxes ADD COLUMN bottle_dep BOOLEAN NOT NULL default FALSE;
ALTER TABLE items_history ADD COLUMN sales_tax BOOLEAN NOT NULL default FALSE;
ALTER TABLE items_history ADD COLUMN bottle_dep BOOLEAN NOT NULL default FALSE;

ALTER TYPE transaction_type ADD VALUE 'cashdeposit';
UPDATE transactions set type='cashdeposit' where type='deposit';
