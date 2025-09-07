# Pokemon Sealed Products Tracker & Transaction Manager

A comprehensive Pokemon TCG sealed products price tracker and portfolio management system with a modern web interface. Track prices for Pokemon TCG sealed products from the Sun & Moon era onwards (2020+) and manage your personal collection transactions.

## Features

### 🎯 Portfolio Management
- **Transaction Tracking**: Buy, sell, and open transactions for Pokemon sealed products
- **Purchase Tracking**: Track purchase method (online/in-person) and location for BUY transactions
- **Portfolio Analytics**: Real-time portfolio value, cost basis, and profit/loss tracking
- **Interactive Charts**: Visual portfolio performance over time using Plotly
- **Advanced Search**: Fuzzy search with multiple algorithms for easy product discovery

### 📊 Price Tracking
- **Daily Price Monitoring**: Automated price checks for 1,590+ sealed products
- **Historical Data**: Comprehensive price history with trend analysis
- **Market Intelligence**: Track low, mid, high, market, and direct prices
- **Parquet Storage**: Efficient data storage (94% smaller than CSV)

### 🖥️ Modern Web Interface
- **FastAPI Backend**: High-performance API with automatic documentation
- **Vue.js Frontend**: Responsive, modern UI with Tailwind CSS
- **Real-time Search**: Advanced fuzzy matching for product discovery
- **Mobile Friendly**: Works perfectly on all devices

## Quick Start

### Option 1: Simple Start
```bash
./start.sh
```

### Option 2: Manual Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python fastapi_app.py
```

### Option 3: With Setup Script
```bash
# Full setup and run
./run_transaction_tracker.sh
```

**Access the Application**: Open `http://localhost:8000` in your browser

## Web Application Features

### 🔍 Advanced Product Search
The search system uses multiple fuzzy matching algorithms:
- **Partial Ratio**: Great for substring matches ("char upc" finds "Charizard UPC")
- **Token Sort**: Handles word reordering ("UPC Charizard" finds "Charizard UPC")
- **Token Set**: Partial word matching ("base boost" finds "Base Set Booster")

### 📈 Portfolio Management
- **Add Transactions**: Easy form with product search, purchase method, and location tracking
- **View Holdings**: Current portfolio with real-time market values
- **Transaction History**: Complete transaction log with purchase details and editing capabilities
- **Performance Tracking**: Visual charts showing portfolio growth over time
- **Purchase Analytics**: Track spending patterns by store and purchase method

### 💡 Smart Features
- **Date Validation**: Automatically adjusts transaction dates to product availability
- **Quantity Tracking**: Real-time inventory for sell/open transactions
- **Price Calculation**: Automatic total calculations and cost basis tracking
- **Responsive Design**: Beautiful interface that works on all screen sizes

## System Architecture

### Core Components
- **`fastapi_app.py`** - Main web application with FastAPI backend
- **`transaction_manager.py`** - Business logic for portfolio management
- **`database.py`** - SQLite database operations
- **`templates/index.html`** - Modern Vue.js frontend interface

### Price Tracking Scripts
- **`daily_price_checker_parquet.py`** - Main daily price checker using Parquet format
- **`historical_data_collector.py`** - Collect and process historical price data
- **`product_discovery.py`** - Discover and catalog sealed products

### Data Files
- **`pokemon_transactions.db`** - SQLite database with transactions and portfolio data
- **`sealed_products_tracking.csv`** - Master list of 1,590 sealed products
- **`daily_prices/`** - Parquet files with daily price snapshots

## Database Schema

The SQLite database includes tables for:
- **transactions** - All buy/sell/open transactions with validation, purchase method, and location tracking
- **portfolio_holdings** - Current holdings with cost basis
- **daily_portfolio_values** - Historical portfolio performance
- **products** - Product catalog with metadata

### Transaction Fields
- Core: product_id, transaction_type, quantity, price, dates
- Purchase tracking: purchase_method (online/in_person), purchase_location
- Metadata: notes, validation flags, timestamps

## API Endpoints

The FastAPI backend provides RESTful APIs:
- **`GET /api/products/search`** - Advanced fuzzy product search
- **`POST /api/transactions`** - Add new transactions
- **`GET /api/portfolio/summary`** - Portfolio overview statistics
- **`GET /api/portfolio/holdings`** - Current holdings with market values
- **`GET /api/transactions`** - Transaction history with filtering

## Data Coverage

**Total Products**: 1,590 sealed Pokemon TCG products from 90 sets (SM era onwards)

**Sets Covered** (2017-2025):
- SM Base Set through SV: White Flare  
- SWSH series (Sword & Shield era)
- SV series (Scarlet & Violet era)
- Special sets, promos, and trainer products

**Product Types Tracked**:
- Booster boxes and packs
- Elite trainer boxes
- Theme decks and starter sets
- Special collections and tins
- Tournament kits and battle academies

**Current Market Data**:
- Products with market prices: 1,305 out of 1,590
- Average market price: $209.12
- Median market price: $46.56
- Price range: $0.68 - $11,918.49

## Storage Format: Parquet Efficiency

**Parquet Benefits**:
- 94% smaller files (18.4 KB vs 307 KB per day)
- 85% faster reading (0.54ms vs 3.64ms)
- Columnar efficiency for analytics
- Yearly storage: 6.6 MB vs 109.4 MB for CSV

### Directory Structure
```
daily_prices/
├── market_prices_2025-09-04.parquet
├── market_prices_2025-09-05.parquet
└── all_market_prices.parquet
```

## Automation & Deployment

### Daily Price Updates
Set up automated daily price checks with cron:
```bash
# Edit crontab
crontab -e

# Add line to run daily at 9 AM
0 9 * * * /path/to/project/run_daily_check_parquet.sh
```

### Production Deployment
For production use, consider:
```bash
# Using Gunicorn for production
pip install gunicorn
gunicorn fastapi_app:app -w 4 -k uvicorn.workers.UvicornWorker

# Or with Docker (create Dockerfile as needed)
# docker build -t pokemon-tracker .
# docker run -p 8000:8000 pokemon-tracker
```

## Development

### Key Files Structure
```
Pokemon_Sealed_Tracker/
├── fastapi_app.py              # Main web application
├── transaction_manager.py      # Business logic
├── database.py                 # Database operations
├── templates/index.html        # Frontend interface
├── pokemon_transactions.db     # SQLite database
├── sealed_products_tracking.csv
├── daily_prices/              # Parquet price data
└── requirements.txt           # Dependencies
```

### API Documentation
When running the application, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Data Sources

All price data comes from TCGPlayer API via tcgcsv.com:
- Low price, Mid price, High price
- Market price, Direct low price
- Comprehensive market data for investment decisions
