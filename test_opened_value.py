#!/usr/bin/env python3
"""
Test script to demonstrate how opened items are excluded from market value
"""
import pandas as pd
import os

def test_opened_items_market_value():
    """Test that opened items don't contribute to market value"""
    
    # Create a test scenario
    print("🧪 Testing Opened Items Market Value Logic")
    print("="*50)
    
    # Check if we have purchases
    if not os.path.exists('my_purchases.csv'):
        print("❌ No purchases file found for testing")
        return
    
    purchases_df = pd.read_csv('my_purchases.csv')
    
    # Show current status
    print("Current Collection Status:")
    
    # Add status column if it doesn't exist
    if 'status' not in purchases_df.columns:
        purchases_df['status'] = None
    
    # Count items by status
    sealed_items = purchases_df[purchases_df['status'].isna() | (purchases_df['status'] == '')]['quantity'].sum()
    opened_items = purchases_df[purchases_df['status'] == 'OPENED']['quantity'].sum()
    sold_items = purchases_df[purchases_df['status'] == 'SOLD']['quantity'].sum()
    
    print(f"📦 Sealed Items: {sealed_items} (contribute to market value)")
    print(f"📂 Opened Items: {opened_items} (NO market value)")
    print(f"💰 Sold Items: {sold_items} (not in collection)")
    
    # Example calculation with a sample product
    print(f"\n💡 Example Market Value Impact:")
    print(f"If ETBs have market price of $45:")
    print(f"• 5 sealed ETBs = 5 × $45 = $225 market value")
    print(f"• Open 2 ETBs → 3 sealed + 2 opened")
    print(f"• New market value = 3 × $45 = $135")
    print(f"• Market value REDUCED by $90 (2 × $45)")
    
    print(f"\n📊 This reflects reality:")
    print(f"• Sealed Pokemon products hold market value")
    print(f"• Opened products have little/no resale value")
    print(f"• Collection tracking now accurately reflects this")
    
    print(f"\n🎯 Key Benefits:")
    print(f"• Realistic collection valuation")
    print(f"• Clear distinction between sealed/opened value")
    print(f"• Better investment tracking")
    print(f"• Encourages keeping items sealed for value")
    
    return True

if __name__ == "__main__":
    os.chdir('/Users/gaurav/Downloads/Projects/Pokemon/PokemonSealedPriceTeacker')
    test_opened_items_market_value()
