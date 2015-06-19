ALTER TYPE public.transaction_type ADD VALUE 'ccdeposit';
ALTER TABLE transactions ADD COLUMN stripe_id TEXT;
ALTER TABLE transactions ADD COLUMN cc_last4 TEXT;
