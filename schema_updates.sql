-- Remove soft delete column and add indexes for better performance

-- Remove is_deleted column (if you want to clean up the schema)
-- Note: This will require a backup and migration
-- ALTER TABLE transactions DROP COLUMN is_deleted;

-- Add performance indexes
CREATE INDEX IF NOT EXISTS idx_transactions_product_id ON transactions(product_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_composite ON transactions(product_id, transaction_date, transaction_type);

-- Add indexes for portfolio tables
CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_product ON portfolio_holdings(product_id);
CREATE INDEX IF NOT EXISTS idx_daily_portfolio_date ON daily_portfolio_value(date);

-- Add constraints for data integrity
-- ALTER TABLE transactions ADD CONSTRAINT chk_quantity_positive CHECK (quantity > 0);
-- ALTER TABLE transactions ADD CONSTRAINT chk_price_positive CHECK (price_per_unit IS NULL OR price_per_unit >= 0);
