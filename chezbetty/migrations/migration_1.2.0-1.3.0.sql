ALTER TYPE subtransaction_type ADD VALUE 'restocklinebox';
ALTER TABLE subtransactions ADD COLUMN box_id integer;
ALTER TABLE subtransactions ADD COLUMN coupon_amount numeric;
ALTER TABLE subtransactions ADD COLUMN sales_tax boolean;
ALTER TABLE subtransactions ADD COLUMN bottle_deposit boolean;
ALTER TABLE subtransactions ALTER COLUMN item_id DROP NOT NULL;