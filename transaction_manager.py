import pandas as pd
from datetime import datetime, date
import glob
from pathlib import Path
from database import TransactionDatabase

class TransactionManager:
    def __init__(self, sealed_products_csv="sealed_products_tracking.csv", 
                 daily_prices_dir="daily_prices"):
        self.db = TransactionDatabase()
        self.sealed_products_csv = sealed_products_csv
        self.daily_prices_dir = daily_prices_dir
        self.products_df = pd.read_csv(sealed_products_csv)
        self.products_df['earliestDate'] = pd.to_datetime(self.products_df['earliestDate'])
    
    def get_product_info(self, product_id):
        """Get product information by ID"""
        product = self.products_df[self.products_df['productId'] == product_id]
        if product.empty:
            return None
        return product.iloc[0]
    
    def search_products(self, search_term, limit=20):
        """Search products by name with fuzzy matching"""
        if not search_term:
            return self.products_df.head(limit)
        
        # Simple contains search for now, can be enhanced with fuzzy matching
        mask = self.products_df['name'].str.contains(search_term, case=False, na=False)
        return self.products_df[mask].head(limit)
    
    def validate_transaction_date(self, product_id, input_date):
        """Validate and adjust transaction date against product's earliest date"""
        product_info = self.get_product_info(product_id)
        if product_info is None:
            raise ValueError(f"Product ID {product_id} not found")
        
        earliest_date = product_info['earliestDate']
        input_date = pd.to_datetime(input_date)
        
        if input_date < earliest_date:
            return earliest_date.date(), True  # date, was_adjusted
        return input_date.date(), False
    
    def validate_inventory(self, product_id, quantity, transaction_type):
        """Validate that sufficient inventory exists for SELL/OPEN transactions"""
        if transaction_type == 'BUY':
            return True
        
        # Get current holdings
        holdings = self.db.get_portfolio_holdings()
        if holdings.empty:
            return False
        
        product_holding = holdings[holdings['product_id'] == product_id]
        if product_holding.empty:
            return False
        
        current_quantity = product_holding.iloc[0]['current_quantity']
        return current_quantity >= quantity
    
    def add_transaction(self, product_id, transaction_type, quantity, input_date, 
                       price_per_unit=None, notes=""):
        """Add a new transaction with validation"""
        # Validate product exists
        product_info = self.get_product_info(product_id)
        if product_info is None:
            raise ValueError(f"Product ID {product_id} not found")
        
        product_name = product_info['name']
        
        # Validate and adjust date
        transaction_date, date_adjusted = self.validate_transaction_date(product_id, input_date)
        
        # Validate inventory for SELL/OPEN
        if transaction_type in ['SELL', 'OPEN']:
            if not self.validate_inventory(product_id, quantity, transaction_type):
                current_qty = self.get_current_quantity(product_id)
                raise ValueError(f"Insufficient inventory. Current quantity: {current_qty}, Requested: {quantity}")
        
        # Validate price for BUY/SELL
        if transaction_type in ['BUY', 'SELL'] and price_per_unit is None:
            raise ValueError(f"Price per unit is required for {transaction_type} transactions")
        
        if transaction_type == 'OPEN' and price_per_unit is not None:
            price_per_unit = None  # Force None for OPEN transactions
        
        # Add transaction to database
        transaction_id = self.db.add_transaction(
            product_id=product_id,
            product_name=product_name,
            transaction_type=transaction_type,
            quantity=quantity,
            price_per_unit=price_per_unit,
            transaction_date=transaction_date,
            input_date=pd.to_datetime(input_date).date(),
            date_adjusted=date_adjusted,
            notes=notes
        )
        
        # Update portfolio holdings
        self.db.update_portfolio_holdings(product_id, product_name)
        
        # Recalculate daily portfolio values from transaction date forward
        self.recalculate_daily_values_from_date(transaction_date)
        
        return transaction_id
    
    def get_current_quantity(self, product_id):
        """Get current quantity for a product"""
        holdings = self.db.get_portfolio_holdings()
        if holdings.empty:
            return 0
        
        product_holding = holdings[holdings['product_id'] == product_id]
        if product_holding.empty:
            return 0
        
        return product_holding.iloc[0]['current_quantity']
    
    def get_market_price(self, product_id, date):
        """Get market price for a product on a specific date"""
        date_str = date.strftime('%Y-%m-%d')
        parquet_file = f"{self.daily_prices_dir}/market_prices_{date_str}.parquet"
        
        try:
            prices_df = pd.read_parquet(parquet_file)
            price_row = prices_df[prices_df['productId'] == product_id]
            if not price_row.empty:
                return price_row.iloc[0]['marketPrice']
        except FileNotFoundError:
            pass
        
        return None
    
    def calculate_portfolio_value_for_date(self, target_date):
        """Calculate total portfolio value for a specific date"""
        # Get all transactions up to this date
        all_transactions = self.db.get_transactions()
        
        if all_transactions.empty:
            return 0, 0  # cost_basis, market_value
        
        # Filter transactions up to target date
        all_transactions['transaction_date'] = pd.to_datetime(all_transactions['transaction_date'])
        relevant_transactions = all_transactions[all_transactions['transaction_date'] <= pd.to_datetime(target_date)]
        
        total_cost_basis = 0
        total_market_value = 0
        
        # Group by product and calculate holdings
        for product_id in relevant_transactions['product_id'].unique():
            product_transactions = relevant_transactions[relevant_transactions['product_id'] == product_id]
            
            # Calculate quantities
            bought = product_transactions[product_transactions['transaction_type'] == 'BUY']
            sold = product_transactions[product_transactions['transaction_type'] == 'SELL']
            opened = product_transactions[product_transactions['transaction_type'] == 'OPEN']
            
            total_bought = bought['quantity'].sum() if not bought.empty else 0
            total_sold = sold['quantity'].sum() if not sold.empty else 0
            total_opened = opened['quantity'].sum() if not opened.empty else 0
            current_quantity = total_bought - total_sold - total_opened
            
            if current_quantity <= 0:
                continue
            
            # Calculate cost basis
            buy_cost = (bought['quantity'] * bought['price_per_unit']).sum() if not bought.empty else 0
            sell_revenue = (sold['quantity'] * sold['price_per_unit']).sum() if not sold.empty else 0
            product_cost_basis = buy_cost - sell_revenue
            
            # Get market value
            market_price = self.get_market_price(product_id, target_date)
            product_market_value = current_quantity * market_price if market_price else 0
            
            total_cost_basis += product_cost_basis
            total_market_value += product_market_value
        
        return total_cost_basis, total_market_value
    
    def recalculate_daily_values_from_date(self, start_date):
        """Recalculate daily portfolio values from a given date forward"""
        # Get all available price dates from start_date onward
        price_files = glob.glob(f"{self.daily_prices_dir}/market_prices_*.parquet")
        available_dates = []
        
        for file in price_files:
            date_str = Path(file).stem.replace('market_prices_', '')
            file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if file_date >= start_date:
                available_dates.append(file_date)
        
        available_dates.sort()
        
        # Calculate and store daily values
        for calc_date in available_dates:
            cost_basis, market_value = self.calculate_portfolio_value_for_date(calc_date)
            unrealized_pnl = market_value - cost_basis
            
            # Update database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_portfolio_value 
                (date, total_cost_basis, total_market_value, unrealized_pnl)
                VALUES (?, ?, ?, ?)
            ''', (calc_date.strftime('%Y-%m-%d'), cost_basis, market_value, unrealized_pnl))
            
            conn.commit()
            conn.close()
    
    def get_portfolio_summary(self):
        """Get current portfolio summary"""
        holdings = self.db.get_portfolio_holdings()
        if holdings.empty:
            return {
                'total_products': 0,
                'total_quantity': 0,
                'total_cost_basis': 0,
                'current_market_value': 0,
                'unrealized_pnl': 0
            }
        
        # Get latest market values
        latest_daily_value = self.db.get_daily_portfolio_value()
        if not latest_daily_value.empty:
            latest = latest_daily_value.iloc[-1]
            current_market_value = latest['total_market_value']
            total_cost_basis = latest['total_cost_basis']
            unrealized_pnl = latest['unrealized_pnl']
        else:
            current_market_value = 0
            total_cost_basis = holdings['total_cost_basis'].sum()
            unrealized_pnl = 0
        
        return {
            'total_products': len(holdings),
            'total_quantity': holdings['current_quantity'].sum(),
            'total_cost_basis': total_cost_basis,
            'current_market_value': current_market_value,
            'unrealized_pnl': unrealized_pnl
        }
