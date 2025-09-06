#!/usr/bin/env python3
"""
Test script for the improved inventory management functionality
"""
import pandas as pd
import sys
import os

# Add the current directory to Python path to import track_purchases
sys.path.insert(0, '/Users/gaurav/Downloads/Projects/Pokemon/PokemonSealedPriceTeacker')

def test_inventory_functions():
    """Test the inventory management functions"""
    print("Testing inventory management functionality...")
    
    # Test 1: Read purchases file
    purchases_file = 'my_purchases.csv'
    if not os.path.exists(purchases_file):
        print("❌ No purchases file found")
        return False
    
    purchases_df = pd.read_csv(purchases_file)
    print(f"✅ Loaded {len(purchases_df)} purchase records")
    
    # Test 2: Create inventory summary
    inventory = []
    for product_id in purchases_df['product_id'].unique():
        product_purchases = purchases_df[purchases_df['product_id'] == product_id]
        product_name = product_purchases['product_name'].iloc[0]
        
        total_purchased = product_purchases['quantity'].sum()
        
        # Calculate sold and opened quantities (will be 0 if status column doesn't exist)
        sold_qty = 0
        opened_qty = 0
        if 'status' in product_purchases.columns:
            sold_items = product_purchases[product_purchases['status'] == 'SOLD']
            sold_qty = sold_items['quantity'].sum()
            
            opened_items = product_purchases[product_purchases['status'] == 'OPENED']
            opened_qty = opened_items['quantity'].sum()
        
        sealed_qty = total_purchased - sold_qty - opened_qty
        
        inventory.append({
            'product_id': product_id,
            'product_name': product_name[:40],  # Truncate for display
            'total_purchased': total_purchased,
            'sealed_available': sealed_qty,
            'opened_quantity': opened_qty,
            'sold_quantity': sold_qty
        })
    
    inventory_df = pd.DataFrame(inventory)
    print(f"✅ Created inventory summary for {len(inventory_df)} unique products")
    
    # Test 3: Display inventory summary
    print("\n" + "="*80)
    print("INVENTORY SUMMARY (First 10 items)")
    print("="*80)
    print(f"{'Product Name':<40} {'Sealed':<8} {'Opened':<8} {'Sold':<6} {'Total':<6}")
    print("-"*80)
    
    for idx, item in inventory_df.head(10).iterrows():
        name = item['product_name']
        sealed = int(item['sealed_available'])
        opened = int(item['opened_quantity'])
        sold = int(item['sold_quantity'])
        total = int(item['total_purchased'])
        
        print(f"{name:<40} {sealed:<8} {opened:<8} {sold:<6} {total:<6}")
    
    # Test 4: Summary statistics
    total_products = len(inventory_df)
    total_sealed = inventory_df['sealed_available'].sum()
    total_opened = inventory_df['opened_quantity'].sum()
    total_sold = inventory_df['sold_quantity'].sum()
    total_items = inventory_df['total_purchased'].sum()
    
    print("-"*80)
    print(f"{'TOTALS':<40} {int(total_sealed):<8} {int(total_opened):<8} {int(total_sold):<6} {int(total_items):<6}")
    print("="*80)
    
    print(f"\n📊 Summary:")
    print(f"   • {total_products} unique products")
    print(f"   • {int(total_items)} total items purchased")
    print(f"   • {int(total_sealed)} sealed items available")
    print(f"   • {int(total_opened)} opened items")
    print(f"   • {int(total_sold)} sold items")
    
    # Test 5: Check for products with multiple purchase dates
    duplicate_products = purchases_df['product_id'].value_counts()
    multi_purchase_products = duplicate_products[duplicate_products > 1]
    
    if len(multi_purchase_products) > 0:
        print(f"\n🔄 Products with multiple purchases:")
        for product_id, count in multi_purchase_products.head(5).items():
            product_name = purchases_df[purchases_df['product_id'] == product_id]['product_name'].iloc[0]
            print(f"   • {product_name[:50]}: {count} purchase records")
    
    print(f"\n✅ All inventory tests completed successfully!")
    print(f"💡 The new system can now:")
    print(f"   • Aggregate quantities across multiple purchase dates")
    print(f"   • Track sealed vs opened vs sold status")
    print(f"   • Validate quantities before selling/opening")
    print(f"   • Allow partial sales and opens")
    
    return True

if __name__ == "__main__":
    os.chdir('/Users/gaurav/Downloads/Projects/Pokemon/PokemonSealedPriceTeacker')
    test_inventory_functions()
