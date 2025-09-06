# Pokemon Transaction Tracker

A transaction tracking system for your Pokemon sealed product collection that integrates with your existing price tracking infrastructure.

## Features

- **Transaction Management**: Track BUY, SELL, and OPEN transactions
- **Intelligent Date Validation**: Automatically adjusts transaction dates to product release dates
- **Inventory Validation**: Ensures sufficient inventory for SELL/OPEN transactions
- **Fuzzy Product Search**: Easy product selection with intelligent search
- **Portfolio Tracking**: Real-time cost basis and market value calculations
- **Interactive Charts**: Visual portfolio performance over time
- **Web-based UI**: Clean, intuitive Streamlit interface

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test the System
```bash
python3 test_transaction_system.py
```

### 3. Run the Application
```bash
./run_transaction_tracker.sh
```

Or manually:
```bash
streamlit run streamlit_app.py
```

## Transaction Types

### BUY Transactions
- **Purpose**: Record purchases of sealed products
- **Required**: Product, quantity, date, price per unit
- **Effect**: 
  - Increases cost basis
  - Increases collection value
  - Adds to inventory

### SELL Transactions  
- **Purpose**: Record sales of sealed products
- **Required**: Product, quantity, date, price per unit
- **Validation**: Must have sufficient inventory
- **Effect**:
  - Decreases cost basis by sale amount
  - Decreases collection value
  - Removes from inventory

### OPEN Transactions
- **Purpose**: Record opening sealed products
- **Required**: Product, quantity, date
- **Validation**: Must have sufficient inventory
- **Effect**:
  - No change to cost basis
  - Decreases collection value
  - Removes from inventory

## Key Features

### Date Validation
The system automatically ensures transaction dates are valid:
- If you enter a date before a product's release date, it's automatically adjusted
- The system tracks both your input date and the adjusted date
- You'll be notified when dates are adjusted

### Fuzzy Search
Product selection uses intelligent fuzzy search:
- Type partial product names
- Searches both name and clean name fields
- Shows relevant results even with typos
- Displays product ID for verification

### Portfolio Calculations
Daily portfolio values are calculated by:
1. Getting all transactions up to each date
2. Calculating current holdings for each product
3. Applying market prices from your daily price files
4. Computing total cost basis and market value

## Database Schema

### Transactions Table
- `transaction_id`: Unique identifier
- `product_id`: Links to sealed_products_tracking.csv
- `product_name`: Denormalized for easy display
- `transaction_type`: BUY, SELL, or OPEN
- `quantity`: Number of items
- `price_per_unit`: Price (NULL for OPEN)
- `total_amount`: Calculated total
- `transaction_date`: Effective date for calculations
- `input_date`: Original date entered
- `date_adjusted`: Whether date was modified
- `created_at`: When transaction was entered
- `notes`: Optional notes

### Portfolio Holdings Table
- Tracks current inventory and cost basis per product
- Updated automatically when transactions are added

### Daily Portfolio Value Table
- Stores daily snapshots for charting
- Rebuilt when transactions are added/modified

## Integration with Existing System

The transaction tracker integrates seamlessly with your current setup:

### Preserves Existing Data
- `sealed_products_tracking.csv` - Used for product information
- `daily_prices/*.parquet` - Used for market value calculations
- Your existing price checking scripts continue to work

### New Components Added
- `pokemon_transactions.db` - SQLite database for transactions
- `streamlit_app.py` - Web interface
- `transaction_manager.py` - Core business logic
- `database.py` - Database operations

## File Structure

```
/Pokemon_Sealed_Tracker/
├── sealed_products_tracking.csv     # Existing product data
├── daily_prices/                    # Existing price data
├── pokemon_transactions.db          # New transaction database
├── streamlit_app.py                 # Web interface
├── transaction_manager.py           # Business logic
├── database.py                      # Database operations
├── test_transaction_system.py       # System tests
├── run_transaction_tracker.sh       # Launch script
└── requirements.txt                 # Updated dependencies
```

## Usage Examples

### Adding a Purchase
1. Select "Add Transaction" from sidebar
2. Choose "BUY" transaction type
3. Search for product (e.g., "Evolving Skies Elite")
4. Enter quantity and price
5. Select date
6. Click "Add Transaction"

### Viewing Portfolio
1. Select "Portfolio Overview" from sidebar
2. View summary metrics
3. Check the portfolio value chart
4. Review current holdings table

### Transaction History
1. Select "Transaction History" from sidebar
2. Filter by transaction type if needed
3. View all past transactions

## Troubleshooting

### Database Issues
If you encounter database errors:
```bash
rm pokemon_transactions.db
python3 test_transaction_system.py
```

### Missing Dependencies
If imports fail:
```bash
pip install -r requirements.txt
```

### Date Validation Errors
- Ensure your `sealed_products_tracking.csv` has `earliestDate` column
- Check that dates are in YYYY-MM-DD format

## Development Notes

### Adding New Features
- Database schema changes: Update `database.py`
- Business logic: Modify `transaction_manager.py`
- UI changes: Edit `streamlit_app.py`

### Performance Considerations
- Daily portfolio values are cached in database
- Large portfolios may take time to recalculate
- Consider adding indexes for better query performance

## Support

For issues or questions:
1. Run the test script to verify system health
2. Check error messages in the Streamlit interface
3. Review transaction history for data validation
