#!/usr/bin/env python3
"""
Delete a specific transaction and update all related data
"""

import sqlite3
import pandas as pd
import sys
from transaction_manager import TransactionManager

def delete_transaction_and_update(transaction_id):
    """Delete transaction and update all related data"""
    
    print(f"🗑️ Deleting transaction {transaction_id} and updating portfolio...")
    
    # Connect to database
    conn = sqlite3.connect('pokemon_transactions.db')
    cursor = conn.cursor()
    
    # First, get the transaction details before deletion
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    transaction = cursor.fetchone()
    
    if not transaction:
        print(f"❌ Transaction {transaction_id} not found!")
        conn.close()
        return False
    
    # Extract transaction details
    trans_id, product_id, product_name, trans_type, quantity, price_per_unit, total_amount, trans_date, input_date, date_adjusted, created_at, notes, is_deleted = transaction
    
    print(f"📋 Transaction Details:")
    print(f"   Product: {product_name} (ID: {product_id})")
    print(f"   Type: {trans_type}")
    print(f"   Quantity: {quantity}")
    print(f"   Price: ${price_per_unit} each" if price_per_unit else "No price (OPEN)")
    print(f"   Total: ${total_amount}" if total_amount else "N/A")
    print(f"   Date: {trans_date}")
    print(f"   Currently deleted: {'Yes' if is_deleted else 'No'}")
    
    # Permanently delete the transaction
    cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))
    deleted_rows = cursor.rowcount
    
    if deleted_rows == 0:
        print(f"❌ No transaction deleted (may not exist)")
        conn.close()
        return False
    
    print(f"✅ Transaction {transaction_id} permanently deleted from database")
    
    # Commit the deletion
    conn.commit()
    conn.close()
    
    # Now update portfolio holdings for this product
    print(f"🔄 Updating portfolio holdings for product {product_id}...")
    
    tm = TransactionManager()
    tm.db.update_portfolio_holdings(product_id, product_name)
    
    print(f"✅ Portfolio holdings updated for {product_name}")
    
    # Recalculate daily portfolio values from the transaction date onward
    print(f"📊 Recalculating daily portfolio values from {trans_date}...")
    
    trans_date_obj = pd.to_datetime(trans_date).date()
    tm.recalculate_daily_values_from_date(trans_date_obj)
    
    print(f"✅ Daily portfolio values recalculated")
    
    return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 delete_transaction.py <transaction_id>")
        print("Example: python3 delete_transaction.py 53")
        sys.exit(1)
    
    try:
        transaction_id = int(sys.argv[1])
    except ValueError:
        print("Error: Transaction ID must be a number")
        sys.exit(1)
    
    print(f"🃏 Pokemon Transaction Deleter")
    print("=" * 40)
    
    # Confirm deletion
    response = input(f"⚠️  Are you sure you want to PERMANENTLY delete transaction {transaction_id}? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Delete transaction and update everything
    success = delete_transaction_and_update(transaction_id)
    
    if success:
        print("\n🎉 Transaction deletion complete!")
        print("✅ Transaction permanently removed")
        print("✅ Portfolio holdings updated")
        print("✅ Daily values recalculated")
        print("\n💡 Next time you run the Streamlit app, all data will be current.")
    else:
        print("\n❌ Transaction deletion failed!")

if __name__ == "__main__":
    main()
