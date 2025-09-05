# Pokemon Sealed Products Price Tracker (SM Era & Beyond)

This project tracks prices for Pokemon TCG sealed products from the Sun & Moon era onwards (2020+) that don't have individual card rarity/numbering information.

## Key Requirements & Filters

- **Time Period**: Only products modified in 2020 or later
- **Product Type**: Sealed products missing both `extRarity` and `extNumber` fields
- **Sets Covered**: SM Promos through current SV sets (90 sets total)
- **Required Fields**: productId, name, cleanName, imageUrl, modifiedOn

## Files Created

### Data Files
- `sealed_products_tracking.csv` - Master list of 1,590 sealed products (2020+) with detailed info
- `sealed_product_ids.txt` - Simple text file with product IDs (one per line)
- `historical_prices.csv` - Growing database of daily price checks
- `price_check_YYYY-MM-DD.csv` - Daily price snapshots

## Scripts

### Primary Scripts (Parquet-based - Recommended)
- `daily_price_checker_parquet.py` - **Main daily price checker using Parquet format**
- `price_analyzer_parquet.py` - **Price analysis using Parquet files**
- `run_daily_check_parquet.sh` - **Automated daily runner for Parquet system**

### Legacy Scripts (CSV-based)
- `daily_price_checker.py` - Original CSV-based price checker
- `price_analyzer.py` - Original CSV-based price analyzer
- `run_daily_check.sh` - Original CSV automation script

### Utility Scripts
- `a.py` - Main discovery script that identifies sealed products
- `storage_comparison.py` - Compare CSV vs Parquet efficiency

## Storage Format: Parquet vs CSV

**Parquet Format (Recommended)**:
- **94% smaller files** (18.4 KB vs 307 KB per day)
- **85% faster reading** (0.54ms vs 3.64ms)
- **Columnar efficiency** for analytics
- **Yearly storage**: 6.6 MB vs 109.4 MB for CSV

### Parquet Files Structure
```
daily_prices/
├── market_prices_2025-09-04.parquet  # Daily files (productId, marketPrice)
├── market_prices_2025-09-05.parquet
├── all_market_prices.parquet          # Master file (date, productId, marketPrice)
└── ...
```

## What Products Are Being Tracked

**Total Products**: 1,590 sealed Pokemon TCG products from 90 sets (SM era onwards)

**Sets Covered** (2017-2025):
- SM Base Set through SV: White Flare
- SWSH series (Sword & Shield era)
- SV series (Scarlet & Violet era)
- Special sets, promos, and trainer products

These are products that don't have individual card rarity (`extRarity`) or card numbers (`extNumber`), which typically indicates they are sealed products like:
- Booster boxes and packs
- Elite trainer boxes
- Theme decks and starter sets
- Special collections and tins
- Tournament kits and battle academies

## Current Price Statistics

Based on the focused dataset (2020+):
- **Products with market prices**: 1,305 out of 1,590
- **Average market price**: $209.12
- **Median market price**: $46.56
- **Highest priced item**: $11,918.49
- **Lowest priced item**: $0.68

## Automation Setup

To run daily price checks automatically, set up a cron job:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * /path/to/your/project/run_daily_check.sh
```

## File Structure

```
PriceTracker/
├── a.py                          # Main discovery script
├── daily_price_checker.py        # Daily price checker
├── price_analyzer.py             # Price analysis tool
├── run_daily_check.sh            # Daily automation script
├── sealed_products_tracking.csv  # Master product list
├── sealed_product_ids.txt        # Product IDs only
├── historical_prices.csv         # All daily price data
├── price_check_2025-09-04.csv   # Today's price snapshot
└── venv/                         # Python virtual environment
```

## Sample Products Being Tracked

- Pokemon 2-Player Starter Set (Revised Base Set) - $199.50
- Base Set Theme Deck "Blackout" - $307.95
- XY Base Set Booster Box - Various prices
- Recent SV sets booster products
- Special promotional items
- Tournament kits and trainer products

## Daily Workflow

1. **Morning**: Automated script runs and checks all 2,495 product prices
2. **Data Storage**: Prices saved to both daily snapshot and historical database
3. **Analysis**: If multiple days of data exist, price change analysis runs automatically
4. **Monitoring**: You can manually run analysis anytime to see price trends

## Data Sources

All price data comes from the TCGPlayer API via tcgcsv.com, which provides:
- Low price
- Mid price  
- High price
- Market price
- Direct low price

The system tracks all price points to give you comprehensive market data for investment decisions.
