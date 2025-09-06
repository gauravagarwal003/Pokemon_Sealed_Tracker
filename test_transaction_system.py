#!/usr/bin/env python3
"""
Test script for the Pokemon Transaction Tracker
This script tests the basic functionality before running the full Streamlit app
"""

import sys
import os
from datetime import date, datetime
import pandas as pd

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import TransactionDatabase
    from transaction_manager import TransactionManager
    print("✅ Successfully imported database and transaction manager modules")
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database initialization...")
    try:
        db = TransactionDatabase("test_pokemon_transactions.db")
        print("✅ Database initialized successfully")
        
        # Test connection
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        expected_tables = ['transactions', 'portfolio_holdings', 'daily_portfolio_value']
        table_names = [table[0] for table in tables]
        
        for expected_table in expected_tables:
            if expected_table in table_names:
                print(f"✅ Table '{expected_table}' created successfully")
            else:
                print(f"❌ Table '{expected_table}' not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_transaction_manager():
    """Test transaction manager functionality"""
    print("\n🔍 Testing transaction manager...")
    try:
        # Initialize with test database
        tm = TransactionManager()
        tm.db = TransactionDatabase("test_pokemon_transactions.db")
        
        print("✅ Transaction manager initialized successfully")
        
        # Test product search
        search_results = tm.search_products("Elite Trainer Box", limit=5)
        if not search_results.empty:
            print(f"✅ Product search working - found {len(search_results)} results")
            
            # Test with first product
            test_product = search_results.iloc[0]
            product_id = test_product['productId']
            product_name = test_product['name']
            
            print(f"✅ Test product: {product_name} (ID: {product_id})")
            
            # Test date validation
            test_date = date(2024, 1, 1)
            validated_date, was_adjusted = tm.validate_transaction_date(product_id, test_date)
            print(f"✅ Date validation working - adjusted: {was_adjusted}")
            
            return True
        else:
            print("❌ No products found in search")
            return False
            
    except Exception as e:
        print(f"❌ Transaction manager test failed: {e}")
        return False

def test_sample_transaction():
    """Test adding a sample transaction"""
    print("\n🔍 Testing sample transaction...")
    try:
        tm = TransactionManager()
        tm.db = TransactionDatabase("test_pokemon_transactions.db")
        
        # Find a product to test with
        search_results = tm.search_products("Elite Trainer Box", limit=1)
        if search_results.empty:
            print("❌ No test products available")
            return False
        
        test_product = search_results.iloc[0]
        product_id = int(test_product['productId'])  # Ensure it's an int
        
        # Add a BUY transaction
        transaction_id = tm.add_transaction(
            product_id=product_id,
            transaction_type='BUY',
            quantity=2,
            input_date=date(2024, 3, 1),
            price_per_unit=50.00,
            notes="Test transaction"
        )
        
        print(f"✅ Successfully added test transaction (ID: {transaction_id})")
        
        # Verify transaction was added
        transactions = tm.db.get_transactions()
        if not transactions.empty:
            print(f"✅ Transaction retrieved from database")
            
            # Check portfolio holdings
            holdings = tm.db.get_portfolio_holdings()
            if not holdings.empty:
                print(f"✅ Portfolio holdings updated")
            else:
                print("⚠️  No portfolio holdings found")
        else:
            print("❌ No transactions found in database")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Sample transaction test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_files():
    """Clean up test files"""
    test_files = ["test_pokemon_transactions.db"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🧹 Cleaned up {file}")

def main():
    print("🃏 Pokemon Transaction Tracker - System Test")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ["sealed_products_tracking.csv", "daily_prices"]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("Please ensure you have the sealed products CSV and daily prices directory.")
        return False
    
    print("✅ Required files found")
    
    # Run tests
    all_tests_passed = True
    
    all_tests_passed &= test_database()
    all_tests_passed &= test_transaction_manager()
    all_tests_passed &= test_sample_transaction()
    
    # Cleanup
    cleanup_test_files()
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nTo start the transaction tracker, run:")
        print("./run_transaction_tracker.sh")
        print("\nOr manually with:")
        print("streamlit run streamlit_app.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
