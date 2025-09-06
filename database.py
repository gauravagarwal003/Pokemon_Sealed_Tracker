import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

class TransactionDatabase:
    def __init__(self, db_path="pokemon_transactions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL', 'OPEN')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                price_per_unit DECIMAL(10,2),
                total_amount DECIMAL(10,2),
                transaction_date DATE NOT NULL,
                input_date DATE NOT NULL,
                date_adjusted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                is_deleted BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Portfolio holdings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                total_quantity_bought INTEGER DEFAULT 0,
                total_quantity_sold INTEGER DEFAULT 0,
                total_quantity_opened INTEGER DEFAULT 0,
                current_quantity INTEGER DEFAULT 0,
                total_cost_basis DECIMAL(10,2) DEFAULT 0,
                average_cost_per_unit DECIMAL(10,2) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily portfolio value table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_portfolio_value (
                date DATE PRIMARY KEY,
                total_cost_basis DECIMAL(10,2) DEFAULT 0,
                total_market_value DECIMAL(10,2) DEFAULT 0,
                unrealized_pnl DECIMAL(10,2) DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def add_transaction(self, product_id, product_name, transaction_type, quantity, 
                       price_per_unit, transaction_date, input_date, date_adjusted, notes=""):
        """Add a new transaction"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        total_amount = None
        if price_per_unit is not None:
            total_amount = quantity * price_per_unit
        
        # Convert date objects to strings for SQLite
        transaction_date_str = transaction_date.strftime('%Y-%m-%d') if hasattr(transaction_date, 'strftime') else str(transaction_date)
        input_date_str = input_date.strftime('%Y-%m-%d') if hasattr(input_date, 'strftime') else str(input_date)
        
        cursor.execute('''
            INSERT INTO transactions 
            (product_id, product_name, transaction_type, quantity, price_per_unit, 
             total_amount, transaction_date, input_date, date_adjusted, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, product_name, transaction_type, quantity, price_per_unit,
              total_amount, transaction_date_str, input_date_str, date_adjusted, notes))
        
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return transaction_id
    
    def get_transactions(self, product_id=None, transaction_type=None, include_deleted=False):
        """Get transactions with optional filtering"""
        conn = self.get_connection()
        
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if not include_deleted:
            query += " AND is_deleted = FALSE"
        
        if product_id:
            query += " AND product_id = ?"
            params.append(product_id)
        
        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)
        
        query += " ORDER BY transaction_date DESC, created_at DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_portfolio_holdings(self):
        """Get current portfolio holdings"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM portfolio_holdings WHERE current_quantity > 0", conn)
        conn.close()
        return df
    
    def update_portfolio_holdings(self, product_id, product_name):
        """Recalculate portfolio holdings for a specific product"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all transactions for this product
        transactions = pd.read_sql_query('''
            SELECT transaction_type, quantity, price_per_unit, total_amount 
            FROM transactions 
            WHERE product_id = ? AND is_deleted = FALSE
        ''', conn, params=[product_id])
        
        if transactions.empty:
            # Remove from portfolio if no transactions
            cursor.execute("DELETE FROM portfolio_holdings WHERE product_id = ?", (product_id,))
        else:
            # Calculate totals - ensure proper numeric types
            bought = transactions[transactions['transaction_type'] == 'BUY']
            sold = transactions[transactions['transaction_type'] == 'SELL']
            opened = transactions[transactions['transaction_type'] == 'OPEN']
            
            total_bought = int(bought['quantity'].sum()) if not bought.empty else 0
            total_sold = int(sold['quantity'].sum()) if not sold.empty else 0
            total_opened = int(opened['quantity'].sum()) if not opened.empty else 0
            current_quantity = total_bought - total_sold - total_opened
            
            # Calculate cost basis using average cost method
            # Cost basis = remaining quantity × average purchase price
            buy_cost = float((bought['quantity'] * bought['price_per_unit']).sum()) if not bought.empty else 0.0
            total_bought_qty = int(bought['quantity'].sum()) if not bought.empty else 0
            
            # Calculate average purchase cost (this stays constant regardless of sells/opens)
            avg_purchase_cost = buy_cost / total_bought_qty if total_bought_qty > 0 else 0.0
            
            # Cost basis is only for the items you still own
            total_cost_basis = current_quantity * avg_purchase_cost if current_quantity > 0 else 0.0
            avg_cost = avg_purchase_cost  # This is your true average cost per unit
            
            # Upsert portfolio holdings
            cursor.execute('''
                INSERT OR REPLACE INTO portfolio_holdings 
                (product_id, product_name, total_quantity_bought, total_quantity_sold, 
                 total_quantity_opened, current_quantity, total_cost_basis, 
                 average_cost_per_unit, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (product_id, product_name, total_bought, total_sold, total_opened,
                  current_quantity, total_cost_basis, avg_cost))
        
        conn.commit()
        conn.close()
    
    def get_daily_portfolio_value(self, start_date=None, end_date=None):
        """Get daily portfolio values for graphing"""
        conn = self.get_connection()
        
        query = "SELECT * FROM daily_portfolio_value"
        params = []
        
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append("date >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("date <= ?")
                params.append(end_date)
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
