#!/usr/bin/env python3
"""
Recalculate all portfolio holdings to fix data type issues
"""

import sqlite3
import pandas as pd
from transaction_manager import TransactionManager

def fix_portfolio_data():
    """Recalculate all portfolio holdings with proper data types"""
    
    print("🔧 Fixing portfolio data types...")
    
    tm = TransactionManager()
    
    # Get all unique product IDs that have transactions
    conn = tm.db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT product_id, product_name 
        FROM transactions 
        WHERE is_deleted = 0
    ''')
    
    products_with_transactions = cursor.fetchall()
    conn.close()
    
    print(f"📊 Found {len(products_with_transactions)} products with transactions")
    
    # Recalculate holdings for each product
    for product_id, product_name in products_with_transactions:
        print(f"🔄 Updating {product_name}...")
        tm.db.update_portfolio_holdings(product_id, product_name)
    
    print("✅ All portfolio holdings updated with correct data types")
    
    # Test the portfolio summary
    print("\n🧪 Testing portfolio summary...")
    summary = tm.get_portfolio_summary()
    
    print("📊 Portfolio Summary:")
    print(f"   Total Products: {summary['total_products']} (type: {type(summary['total_products'])})")
    print(f"   Total Quantity: {summary['total_quantity']} (type: {type(summary['total_quantity'])})")
    print(f"   Total Cost Basis: ${summary['total_cost_basis']:.2f} (type: {type(summary['total_cost_basis'])})")
    print(f"   Current Market Value: ${summary['current_market_value']:.2f} (type: {type(summary['current_market_value'])})")
    print(f"   Unrealized P&L: ${summary['unrealized_pnl']:.2f} (type: {type(summary['unrealized_pnl'])})")
    
    print("\n✅ Portfolio data types fixed! Streamlit should work now.")

if __name__ == "__main__":
    fix_portfolio_data()
