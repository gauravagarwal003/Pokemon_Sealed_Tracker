"""
Portfolio Recompiler
Recalculates all portfolio holdings and daily values from scratch
Called after transactions are modified or new price data is added
"""

import pandas as pd
import sqlite3
import glob
from datetime import datetime, date
from datetime import timedelta
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

def round_price(price):
    """Round price to 2 decimal places using proper decimal handling"""
    if price is None:
        return None
    return float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class PortfolioRecompiler:
    def __init__(self, db_path="pokemon_transactions.db", daily_prices_dir="daily_prices"):
        self.db_path = db_path
        self.daily_prices_dir = daily_prices_dir
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_all_transactions(self):
        """Get all transactions (no soft delete filter needed)"""
        conn = self.get_connection()
        query = """
            SELECT * FROM transactions 
            ORDER BY transaction_date, created_at
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_market_price(self, product_id, target_date):
        """Get market price for a product on a specific date"""
        date_str = target_date.strftime('%Y-%m-%d')
        parquet_file = f"{self.daily_prices_dir}/market_prices_{date_str}.parquet"
        try:
            prices_df = pd.read_parquet(parquet_file)
            # Normalize productId column to string to handle int/string mismatches
            if 'productId' in prices_df.columns:
                try:
                    prices_df['productId'] = prices_df['productId'].astype(str)
                except Exception:
                    # fallback: convert via map(str)
                    prices_df['productId'] = prices_df['productId'].map(lambda x: str(x))
            # Ensure product_id is a string for comparison
            price_row = prices_df[prices_df['productId'] == str(product_id)]
            if not price_row.empty and pd.notna(price_row.iloc[0]['marketPrice']):
                return float(price_row.iloc[0]['marketPrice'])
        except (FileNotFoundError, Exception):
            pass
        return None
    
    def get_available_price_dates(self):
        """Get all available dates with price data"""
        price_files = glob.glob(f"{self.daily_prices_dir}/market_prices_*.parquet")
        dates = []
        
        for file in price_files:
            try:
                date_str = Path(file).stem.replace('market_prices_', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                dates.append(file_date)
            except ValueError:
                continue
        
        return sorted(dates)
    
    def calculate_holdings_at_date(self, transactions_df, target_date):
        """Calculate portfolio holdings at a specific date"""
        # Filter transactions up to target date
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
        relevant_transactions = transactions_df[
            transactions_df['transaction_date'] <= pd.to_datetime(target_date)
        ]
        
        holdings = {}
        
        for product_id in relevant_transactions['product_id'].unique():
            # Ensure product_id is a string for comparison
            product_transactions = relevant_transactions[
                relevant_transactions['product_id'].astype(str) == str(product_id)
            ]
            
            product_name = product_transactions.iloc[0]['product_name']
            
            # Calculate quantities by transaction type
            bought = product_transactions[product_transactions['transaction_type'] == 'BUY']
            sold = product_transactions[product_transactions['transaction_type'] == 'SELL']
            opened = product_transactions[product_transactions['transaction_type'] == 'OPEN']
            
            total_bought = int(bought['quantity'].sum()) if not bought.empty else 0
            total_sold = int(sold['quantity'].sum()) if not sold.empty else 0
            total_opened = int(opened['quantity'].sum()) if not opened.empty else 0
            # Treat OPEN as metadata only: it reduces sealed inventory (market value)
            # but does not change how we compute the accounting-style cost basis here.
            # The user requested the cost-basis to be computed as: SUM(BUY amounts) - SUM(SELL amounts)
            # (i.e. bought_amt - sold_amt). This makes sale proceeds reduce the cost-basis directly.
            cost_basis_quantity = total_bought - total_sold
            sealed_quantity = total_bought - total_sold - total_opened

            # Sum buy and sell amounts (use total_amount when present, otherwise quantity*price_per_unit)
            buy_amount = float(bought['total_amount'].fillna(bought['quantity'] * bought['price_per_unit']).sum()) if not bought.empty else 0.0
            sell_amount = float(sold['total_amount'].fillna(sold['quantity'] * sold['price_per_unit']).sum()) if not sold.empty else 0.0

            # Also compute average purchase cost for display/market adjustments
            buy_cost = float((bought['quantity'] * bought['price_per_unit']).sum()) if not bought.empty else 0.0
            avg_purchase_cost = buy_cost / total_bought if total_bought > 0 else 0.0

            # New cost-basis semantics: total_cost_basis = cumulative buys - cumulative sells
            total_cost_basis = buy_amount - sell_amount
            
            holdings[product_id] = {
                'product_name': product_name,
                # quantity used for cost-basis calculations (OPEN does not affect this)
                'cost_basis_quantity': cost_basis_quantity,
                # quantity of sealed items remaining (used for market value calculation)
                'sealed_quantity': sealed_quantity,
                'total_cost_basis': round_price(total_cost_basis),
                'average_cost_per_unit': round_price(avg_purchase_cost),
                'total_bought': total_bought,
                'total_sold': total_sold,
                'total_opened': total_opened
            }
        
        return holdings
    
    def update_portfolio_holdings_table(self):
        """Update the portfolio_holdings table with current holdings"""
        print("Updating portfolio holdings table...")
        
        transactions_df = self.get_all_transactions()
        if transactions_df.empty:
            print("No transactions found, clearing portfolio holdings")
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM portfolio_holdings")
            conn.commit()
            conn.close()
            return
        
        # Calculate current holdings (using today's date)
        current_holdings = self.calculate_holdings_at_date(transactions_df, date.today())
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing holdings
        cursor.execute("DELETE FROM portfolio_holdings")
        
        # Insert updated holdings
        for product_id, holding in current_holdings.items():
            cursor.execute('''
                INSERT INTO portfolio_holdings 
                (product_id, product_name, total_quantity_bought, total_quantity_sold, 
                 total_quantity_opened, current_quantity, total_cost_basis, 
                 average_cost_per_unit, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                str(product_id),
                str(holding['product_name']),
                int(holding['total_bought']),
                int(holding['total_sold']),
                int(holding['total_opened']),
                int(holding.get('sealed_quantity', 0)),
                float(holding['total_cost_basis']) if holding['total_cost_basis'] is not None else 0.0,
                float(holding['average_cost_per_unit']) if holding['average_cost_per_unit'] is not None else 0.0
            ))
        
        conn.commit()
        conn.close()
        
        print(f"Updated holdings for {len(current_holdings)} products")
    
    def recalculate_daily_portfolio_values(self):
        """Recalculate daily portfolio values for all available dates"""
        print("Recalculating daily portfolio values...")
        
        transactions_df = self.get_all_transactions()
        if transactions_df.empty:
            print("No transactions found, clearing daily portfolio values")
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_portfolio_value")
            conn.commit()
            conn.close()
            return
        
        available_dates = self.get_available_price_dates()
        # Also include any transaction dates so cost-basis changes (BUY/SELL)
        # are reflected on the exact transaction date even when a price file
        # for that date is not present.
        try:
            transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
            tx_dates = sorted(set(transactions_df['transaction_date'].dt.date.tolist()))
            # merge and dedupe
            combined = sorted(set(available_dates + tx_dates))
            
            # Always include today's date to ensure we have current portfolio values
            today = date.today()
            if today not in combined:
                combined.append(today)
            
            available_dates = sorted(combined)
        except Exception:
            pass
        
        if not available_dates:
            print("No price data available")
            return

        # Determine the earliest transaction date to start the portfolio
        try:
            transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
            earliest_tx_date = transactions_df['transaction_date'].min().date()
        except Exception:
            earliest_tx_date = None

        # Only use available price dates on or after the first transaction date
        if earliest_tx_date:
            available_dates = [d for d in available_dates if d >= earliest_tx_date]
            # If there is no price file exactly on the earliest transaction date, still include that date
            if earliest_tx_date not in available_dates:
                # Insert the earliest transaction date at the beginning so the portfolio starts there
                available_dates.insert(0, earliest_tx_date)
            if not available_dates:
                # If filtering somehow removed all dates, fall back to all available dates
                available_dates = self.get_available_price_dates()
        
        print(f"Processing portfolio values for {len(available_dates)} dates from {available_dates[0]} to {available_dates[-1]}")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing daily values
        # Ensure cumulative_realized_pnl column exists (safe to try; ignore if already present)
        try:
            cursor.execute("ALTER TABLE daily_portfolio_value ADD COLUMN cumulative_realized_pnl REAL DEFAULT 0")
        except Exception:
            pass

        cursor.execute("DELETE FROM daily_portfolio_value")
        # Create per_product_cost_history table if not exists (will store per-product cumulative amounts per date)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS per_product_cost_history (
                    product_id TEXT,
                    date TEXT,
                    cumulative_buy_amt REAL,
                    cumulative_sell_amt REAL,
                    cumulative_cost_basis REAL,
                    sealed_quantity INTEGER,
                    cost_basis_quantity INTEGER,
                    average_cost_per_unit REAL,
                    total_cost_basis REAL,
                    PRIMARY KEY (product_id, date)
                )
            ''')
        except Exception:
            pass
        # Create index on product_id for faster lookups
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ppch_product_id ON per_product_cost_history (product_id)')
        except Exception:
            pass
        # Clear existing per-product history
        cursor.execute("DELETE FROM per_product_cost_history")
        
        processed_dates = 0
        cumulative_realized_pnl = 0.0
        for calc_date in available_dates:
            # Compute holdings up to and including calc_date. Our holdings' `total_cost_basis`
            # already follow the requested semantics (buy_amount - sell_amount up to date),
            # so we can just sum them. sealed_quantity is used for market value.
            holdings = self.calculate_holdings_at_date(transactions_df, calc_date)
            total_cost_basis = 0.0
            total_market_value = 0.0
            
            # Use the latest available price if current date doesn't have price data
            latest_price_date = None
            for product_id, holding in holdings.items():
                total_cost_basis += holding['total_cost_basis'] if holding['total_cost_basis'] is not None else 0.0
                sealed_qty = holding.get('sealed_quantity', 0)
                
                # Try to get market price for this date, fall back to latest available
                market_price = self.get_market_price(product_id, calc_date)
                if market_price is None and sealed_qty > 0:
                    # If no price for today, try to find the most recent price
                    price_dates = [d for d in available_dates if d <= calc_date]
                    for price_date in reversed(price_dates):
                        market_price = self.get_market_price(product_id, price_date)
                        if market_price is not None:
                            if latest_price_date is None or price_date > latest_price_date:
                                latest_price_date = price_date
                            break
                
                if market_price and sealed_qty > 0:
                    total_market_value += sealed_qty * market_price

                # Persist per-product cumulative data for this date
                try:
                    # Compute cumulative buy/sell amounts from transactions up to calc_date
                    txs = transactions_df[transactions_df['product_id'].astype(str) == str(product_id)]
                    txs_upto = txs[txs['transaction_date'] <= pd.to_datetime(calc_date)]
                    buy_amt = txs_upto[txs_upto['transaction_type']=='BUY']['total_amount'].fillna(txs_upto[txs_upto['transaction_type']=='BUY']['quantity'] * txs_upto[txs_upto['transaction_type']=='BUY']['price_per_unit']).sum()
                    sell_amt = txs_upto[txs_upto['transaction_type']=='SELL']['total_amount'].fillna(txs_upto[txs_upto['transaction_type']=='SELL']['quantity'] * txs_upto[txs_upto['transaction_type']=='SELL']['price_per_unit']).sum()
                    cumulative_cost_basis = float(buy_amt - sell_amt)
                    cursor.execute('''
                        INSERT OR REPLACE INTO per_product_cost_history
                        (product_id, date, cumulative_buy_amt, cumulative_sell_amt, cumulative_cost_basis, sealed_quantity, cost_basis_quantity, average_cost_per_unit, total_cost_basis)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(product_id), calc_date.strftime('%Y-%m-%d'), float(buy_amt), float(sell_amt), cumulative_cost_basis,
                        int(sealed_qty), int(holding.get('cost_basis_quantity', 0)), float(holding.get('average_cost_per_unit') or 0.0), float(holding.get('total_cost_basis') or 0.0)
                    ))
                except Exception:
                    pass

            # Compute realized P&L for sells on this date (using prior average cost)
            try:
                sells_on_date = transactions_df[
                    (transactions_df['transaction_date'] == pd.to_datetime(calc_date)) &
                    (transactions_df['transaction_type'] == 'SELL')
                ]
                if not sells_on_date.empty:
                    for _, sell in sells_on_date.iterrows():
                        pid = sell['product_id']
                        qty = float(sell['quantity'])
                        proceeds = float(sell['total_amount']) if pd.notna(sell.get('total_amount')) else float(sell.get('quantity', 0) * sell.get('price_per_unit', 0.0))

                        # Compute prior average purchase cost for this product up to and including this date
                        prior_buys = transactions_df[(transactions_df['product_id'].astype(str) == str(pid)) & (transactions_df['transaction_type'] == 'BUY') & (transactions_df['transaction_date'] <= pd.to_datetime(calc_date))]
                        total_buy_qty = prior_buys['quantity'].sum()
                        total_buy_cost = (prior_buys['quantity'] * prior_buys['price_per_unit']).sum()
                        avg_cost = float(total_buy_cost / total_buy_qty) if total_buy_qty and total_buy_qty > 0 else 0.0

                        cost_removed = qty * avg_cost
                        realized = proceeds - cost_removed
                        cumulative_realized_pnl += realized
            except Exception:
                pass
            
            # Calculate unrealized P&L
            unrealized_pnl = total_market_value - total_cost_basis
            
            # Insert daily value
            cursor.execute('''
                INSERT INTO daily_portfolio_value 
                (date, total_cost_basis, total_market_value, unrealized_pnl, cumulative_realized_pnl)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                calc_date.strftime('%Y-%m-%d'),
                round_price(total_cost_basis),
                round_price(total_market_value),
                round_price(unrealized_pnl),
                round_price(cumulative_realized_pnl)
            ))
            
            processed_dates += 1
            if processed_dates % 50 == 0:
                print(f"Processed {processed_dates}/{len(available_dates)} dates...")
        
        conn.commit()
        conn.close()
        
        if latest_price_date and latest_price_date < date.today():
            print(f"Warning: Latest price data is from {latest_price_date}. Portfolio values after this date use the last available prices.")
        
        print(f"Recalculated daily values for {processed_dates} dates")
    
    def get_portfolio_summary(self):
        """Get current portfolio summary statistics"""
        conn = self.get_connection()
        
        # Get holdings summary
        holdings_query = """
            SELECT 
                COUNT(*) as total_products,
                SUM(current_quantity) as total_quantity,
                SUM(total_cost_basis) as total_cost_basis
            FROM portfolio_holdings 
            WHERE current_quantity > 0
        """
        
        cursor = conn.cursor()
        cursor.execute(holdings_query)
        holdings_result = cursor.fetchone()
        
        # Get latest market value
        latest_value_query = """
            SELECT total_market_value, unrealized_pnl
            FROM daily_portfolio_value 
            ORDER BY date DESC 
            LIMIT 1
        """
        
        cursor.execute(latest_value_query)
        latest_value_result = cursor.fetchone()
        
        conn.close()
        
        summary = {
            'total_products': holdings_result[0] or 0,
            'total_quantity': holdings_result[1] or 0,
            'total_cost_basis': float(holdings_result[2] or 0),
            'current_market_value': float(latest_value_result[0] if latest_value_result and latest_value_result[0] else 0),
            'unrealized_pnl': float(latest_value_result[1] if latest_value_result and latest_value_result[1] else 0)
        }
        
        return summary
    
    def recompile_all(self):
        """Full recompilation of portfolio data"""
        print("=== Starting Portfolio Recompilation ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Step 1: Update portfolio holdings
            self.update_portfolio_holdings_table()
            
            # Step 2: Recalculate daily portfolio values
            self.recalculate_daily_portfolio_values()
            
            # Step 3: Display summary
            summary = self.get_portfolio_summary()
            print("\n=== Portfolio Summary ===")
            print(f"Total Products: {summary['total_products']}")
            print(f"Total Quantity: {summary['total_quantity']}")
            print(f"Total Cost Basis: ${summary['total_cost_basis']:,.2f}")
            print(f"Current Market Value: ${summary['current_market_value']:,.2f}")
            print(f"Unrealized P&L: ${summary['unrealized_pnl']:+,.2f}")
            
            if summary['total_cost_basis'] > 0:
                pnl_percentage = (summary['unrealized_pnl'] / summary['total_cost_basis']) * 100
                print(f"Portfolio Return: {pnl_percentage:+.2f}%")
            
            print("\n=== Portfolio Recompilation Complete ===")
            return True
            
        except Exception as e:
            print(f"Error during portfolio recompilation: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main function for portfolio recompilation"""
    recompiler = PortfolioRecompiler()
    success = recompiler.recompile_all()
    
    if not success:
        exit(1)

if __name__ == "__main__":
    main()