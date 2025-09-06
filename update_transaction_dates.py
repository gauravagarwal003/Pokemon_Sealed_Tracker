#!/usr/bin/env python3
"""
Update transaction dates based on updated earliest dates in sealed_products_tracking.csv
This script will check all transactions and adjust dates if they're before the product's earliest date.
"""

import sqlite3
import pandas as pd
from datetime import datetime

def update_transaction_dates():
    print("🔄 Updating transaction dates based on updated earliest dates...")
    
    # Load the updated sealed products data
    try:
        products_df = pd.read_csv('sealed_products_tracking.csv')
        products_df['earliestDate'] = pd.to_datetime(products_df['earliestDate'])
        print(f"✅ Loaded {len(products_df)} products from sealed_products_tracking.csv")
    except Exception as e:
        print(f"❌ Error loading sealed products CSV: {e}")
        return False
    
    # Connect to database
    try:
        conn = sqlite3.connect('pokemon_transactions.db')
        cursor = conn.cursor()
        print("✅ Connected to pokemon_transactions.db")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False
    
    # Get all transactions
    try:
        transactions = pd.read_sql_query('''
            SELECT transaction_id, product_id, transaction_date, input_date, date_adjusted
            FROM transactions 
            WHERE is_deleted = 0
        ''', conn)
        print(f"✅ Found {len(transactions)} active transactions")
    except Exception as e:
        print(f"❌ Error loading transactions: {e}")
        conn.close()
        return False
    
    updates_made = 0
    errors = []
    
    # Check each transaction
    for _, transaction in transactions.iterrows():
        transaction_id = transaction['transaction_id']
        product_id = transaction['product_id']
        current_date = pd.to_datetime(transaction['transaction_date'])
        input_date = pd.to_datetime(transaction['input_date'])
        
        # Find the product's earliest date
        product_info = products_df[products_df['productId'] == product_id]
        
        if product_info.empty:
            errors.append(f"Product ID {product_id} not found in sealed_products_tracking.csv")
            continue
        
        earliest_date = product_info.iloc[0]['earliestDate']
        
        # Check if transaction date needs adjustment
        if current_date < earliest_date:
            # Need to update the transaction date
            new_date = earliest_date.strftime('%Y-%m-%d')
            input_date_str = input_date.strftime('%Y-%m-%d')
            
            try:
                cursor.execute('''
                    UPDATE transactions 
                    SET transaction_date = ?, date_adjusted = 1
                    WHERE transaction_id = ?
                ''', (new_date, transaction_id))
                
                updates_made += 1
                print(f"📅 Updated transaction {transaction_id}: {current_date.strftime('%Y-%m-%d')} → {new_date}")
                
            except Exception as e:
                errors.append(f"Error updating transaction {transaction_id}: {e}")
    
    # Commit changes
    try:
        conn.commit()
        print(f"✅ Committed {updates_made} updates to database")
    except Exception as e:
        print(f"❌ Error committing changes: {e}")
        conn.rollback()
        conn.close()
        return False
    
    conn.close()
    
    # Report results
    print("\n" + "="*50)
    print("📊 Update Summary:")
    print(f"Total transactions checked: {len(transactions)}")
    print(f"Transactions updated: {updates_made}")
    print(f"Errors encountered: {len(errors)}")
    
    if errors:
        print("\n⚠️ Errors:")
        for error in errors:
            print(f"  - {error}")
    
    if updates_made > 0:
        print(f"\n✅ Successfully updated {updates_made} transaction dates!")
        print("💡 Note: Portfolio values will be recalculated when you next run the Streamlit app.")
    else:
        print("\n✅ All transaction dates are already valid - no updates needed!")
    
    return True

def recalculate_portfolio_holdings():
    """Recalculate all portfolio holdings after date updates"""
    print("\n🔄 Recalculating portfolio holdings...")
    
    try:
        conn = sqlite3.connect('pokemon_transactions.db')
        cursor = conn.cursor()
        
        # Get all unique product IDs that have transactions
        cursor.execute('''
            SELECT DISTINCT product_id, product_name 
            FROM transactions 
            WHERE is_deleted = 0
        ''')
        
        products_with_transactions = cursor.fetchall()
        
        for product_id, product_name in products_with_transactions:
            # Get all transactions for this product
            transactions = pd.read_sql_query('''
                SELECT transaction_type, quantity, price_per_unit
                FROM transactions 
                WHERE product_id = ? AND is_deleted = 0
            ''', conn, params=[product_id])
            
            if transactions.empty:
                continue
            
            # Calculate totals
            bought = transactions[transactions['transaction_type'] == 'BUY']
            sold = transactions[transactions['transaction_type'] == 'SELL']
            opened = transactions[transactions['transaction_type'] == 'OPEN']
            
            total_bought = bought['quantity'].sum() if not bought.empty else 0
            total_sold = sold['quantity'].sum() if not sold.empty else 0
            total_opened = opened['quantity'].sum() if not opened.empty else 0
            current_quantity = total_bought - total_sold - total_opened
            
            # Calculate cost basis
            buy_cost = (bought['quantity'] * bought['price_per_unit']).sum() if not bought.empty else 0
            sell_revenue = (sold['quantity'] * sold['price_per_unit']).sum() if not sold.empty else 0
            total_cost_basis = buy_cost - sell_revenue
            
            avg_cost = total_cost_basis / current_quantity if current_quantity > 0 else 0
            
            # Update portfolio holdings
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
        print("✅ Portfolio holdings recalculated successfully!")
        
    except Exception as e:
        print(f"❌ Error recalculating portfolio holdings: {e}")
        return False
    
    return True

def main():
    print("🃏 Pokemon Transaction Date Updater")
    print("=" * 50)
    print("This script will update transaction dates to match the updated earliest dates")
    print("from your sealed_products_tracking.csv file.\n")
    
    # Confirm before proceeding
    response = input("Do you want to proceed with updating transaction dates? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update transaction dates
    if update_transaction_dates():
        # Recalculate portfolio holdings
        recalculate_portfolio_holdings()
        
        print("\n🎉 All updates completed successfully!")
        print("\n💡 Next steps:")
        print("1. The transaction dates have been updated in the database")
        print("2. Portfolio holdings have been recalculated")
        print("3. Daily portfolio values will be recalculated when you run the Streamlit app")
        print("4. Run 'streamlit run streamlit_app.py' to see the updated data")
    else:
        print("❌ Update failed. Please check the errors above.")

if __name__ == "__main__":
    main()
