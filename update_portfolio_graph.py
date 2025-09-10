import sys
from datetime import datetime, timedelta
from transaction_manager import TransactionManager

def update_daily_portfolio_values():
    tm = TransactionManager()
    # Find the latest date in the daily_portfolio_value table
    latest_db_date = None
    try:
        import sqlite3
        conn = sqlite3.connect('pokemon_transactions.db')
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(date) FROM daily_portfolio_value')
        row = cursor.fetchone()
        if row and row[0]:
            latest_db_date = datetime.strptime(row[0], '%Y-%m-%d').date()
        conn.close()
    except Exception as e:
        print(f"Error reading latest date from DB: {e}")
        sys.exit(1)

    # If no date in DB, start from earliest available parquet file
    if latest_db_date is None:
        from pathlib import Path
        import glob
        price_files = glob.glob('daily_prices/market_prices_*.parquet')
        if not price_files:
            print("No parquet files found in daily_prices directory.")
            sys.exit(1)
        dates = [datetime.strptime(Path(f).stem.replace('market_prices_', ''), '%Y-%m-%d').date() for f in price_files]
        start_date = min(dates)
    else:
        # Start from the day after the latest date in DB
        start_date = latest_db_date + timedelta(days=1)

    print(f"Updating daily portfolio values from {start_date}...")
    tm.recalculate_daily_values_from_date(start_date)
    print("Done. The graph and summary will now reflect all available data.")

if __name__ == "__main__":
    update_daily_portfolio_values()
