"""
Portfolio Recompiler
Recalculates all portfolio holdings and daily values from scratch
Called after transactions are modified or new price data is added
"""

import pandas as pd
import sqlite3
import glob
from datetime import datetime, date
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
        """Get all non-deleted transactions"""
        conn = self.get_connection()
        query = """
            SELECT * FROM transactions 
            WHERE is_deleted = FALSE 
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
            current_quantity = total_bought - total_sold - total_opened
            
            if current_quantity <= 0:
                continue
            
            # Calculate cost basis using average cost method
            buy_cost = float((bought['quantity'] * bought['price_per_unit']).sum()) if not bought.empty else 0.0
            avg_purchase_cost = buy_cost / total_bought if total_bought > 0 else 0.0
            total_cost_basis = current_quantity * avg_purchase_cost
            
            holdings[product_id] = {
                'product_name': product_name,
                'current_quantity': current_quantity,
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
                int(holding['current_quantity']),
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
        if not available_dates:
            print("No price data available")
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing daily values
        cursor.execute("DELETE FROM daily_portfolio_value")
        
        processed_dates = 0
        for calc_date in available_dates:
            # Calculate holdings for this date
            holdings = self.calculate_holdings_at_date(transactions_df, calc_date)
            
            total_cost_basis = 0.0
            total_market_value = 0.0
            
            for product_id, holding in holdings.items():
                # Add to cost basis
                total_cost_basis += holding['total_cost_basis']
                
                # Get market price for this date
                market_price = self.get_market_price(product_id, calc_date)
                if market_price:
                    product_market_value = holding['current_quantity'] * market_price
                    total_market_value += product_market_value
            
            # Calculate unrealized P&L
            unrealized_pnl = total_market_value - total_cost_basis
            
            # Insert daily value
            cursor.execute('''
                INSERT INTO daily_portfolio_value 
                (date, total_cost_basis, total_market_value, unrealized_pnl)
                VALUES (?, ?, ?, ?)
            ''', (
                calc_date.strftime('%Y-%m-%d'),
                round_price(total_cost_basis),
                round_price(total_market_value),
                round_price(unrealized_pnl)
            ))
            
            processed_dates += 1
            if processed_dates % 50 == 0:
                print(f"Processed {processed_dates}/{len(available_dates)} dates...")
        
        conn.commit()
        conn.close()
        
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