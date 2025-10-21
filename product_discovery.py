import csv
import requests
import os
import pandas as pd
from io import StringIO

# List of set codes (SM era onwards - 2020+)
set_codes = [
    1861, 1863, 1919, 1938, 1957, 2054, 2069, 2071, 2148, 2155, 2175, 2178, 2205, 2208, 2209, 
    2214, 2278, 2282, 2289, 2295, 2328, 2332, 2364, 2374, 2377, 2409, 2420, 2464, 2480, 2534, 
    2545, 2555, 2585, 2594, 2626, 2675, 2685, 2686, 2701, 2754, 2765, 2776, 2781, 2782, 2807, 
    2848, 2867, 2906, 2931, 2948, 3020, 3040, 3051, 3064, 3068, 3087, 3118, 3150, 3170, 3172, 
    3179, 17674, 17688, 17689, 22872, 22873, 22880, 23095, 23120, 23228, 23237, 23266, 23286, 
    23306, 23323, 23330, 23353, 23381, 23473, 23520, 23529, 23537, 23561, 23651, 23821, 24073, 
    24163, 24269, 24325, 24326, 24380, 24381, 24382
]

# Dictionary to store counts per set
missing_data_counts = {}

# List to store all sealed product information
sealed_products = []

# Loop through the set codes and fetch data
for set_code in set_codes:
    print(f"Processing set {set_code}...")
    response = requests.get(f"https://tcgcsv.com/tcgplayer/3/{set_code}/ProductsAndPrices.csv")
    
    if response.status_code == 200:
        try:
            # Parse the CSV data
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            
            # Check if the required columns exist
            required_columns = ['extRarity', 'extNumber', 'modifiedOn', 'cleanName', 'imageUrl']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"  Skipping set {set_code} - missing required columns: {missing_columns}")
                continue
            
            # Filter for products modified in 2020 or later
            df['modifiedOn'] = pd.to_datetime(df['modifiedOn'], errors='coerce')
            df_recent = df[df['modifiedOn'].dt.year >= 2020]
            
            if len(df_recent) == 0:
                print(f"  Skipping set {set_code} - no products modified in 2020 or later")
                continue
            
            # Count items that don't have extRarity AND don't have extNumber
            # Check for empty strings, NaN values, or None
            missing_ext_rarity = df_recent['extRarity'].isna() | (df_recent['extRarity'] == '') | (df_recent['extRarity'] == 'None')
            missing_ext_number = df_recent['extNumber'].isna() | (df_recent['extNumber'] == '') | (df_recent['extNumber'] == 'None')
            
            # Items missing both extRarity and extNumber (sealed products)
            missing_both = missing_ext_rarity & missing_ext_number
            count = missing_both.sum()
            
            # Get the sealed products for this set
            sealed_items = df_recent[missing_both]
            
            # Add sealed products to our list
            for _, item in sealed_items.iterrows():
                sealed_product = {
                    'productId': item['productId'],
                    'name': item['name'],
                    'cleanName': item['cleanName'],
                    'imageUrl': item['imageUrl'],
                    'modifiedOn': item['modifiedOn'].strftime('%Y-%m-%d') if pd.notna(item['modifiedOn']) else '',
                    'earliestDate': item['modifiedOn'].strftime('%Y-%m-%d') if pd.notna(item['modifiedOn']) else '',
                    'set_code': set_code,
                    'url': item.get('url', '')
                }
                sealed_products.append(sealed_product)
            
            missing_data_counts[set_code] = count
            print(f"  Sealed items found (2020+): {count}")
            
        except Exception as e:
            print(f"  Error processing set {set_code}: {e}")
            continue
        
    else:
        print(f"Failed to retrieve the CSV file for set {set_code}. Status code: {response.status_code}")

# Print summary
print("\n" + "="*50)
print("SUMMARY: Sealed items (modified 2020+, missing both extRarity and extNumber) per set")
print("="*50)

total_missing = 0
for set_code, count in missing_data_counts.items():
    print(f"Set {set_code}: {count}")
    total_missing += count

print(f"\nTotal sealed items found: {total_missing}")
print(f"Total sets processed: {len(missing_data_counts)}")

# Save sealed products to CSV file for daily price tracking
if sealed_products:
    sealed_df = pd.DataFrame(sealed_products)
    sealed_df.to_csv('sealed_products_tracking.csv', index=False)
    print(f"\nSealed products data saved to 'sealed_products_tracking.csv'")
    print(f"Total sealed products to track: {len(sealed_products)}")
    
    # Also save just the product IDs for easy reference
    product_ids = [str(product['productId']) for product in sealed_products]
    with open('sealed_product_ids.txt', 'w') as f:
        for product_id in product_ids:
            f.write(f"{product_id}\n")
    
    print(f"Product IDs saved to 'sealed_product_ids.txt'")
    
    # Show a sample of the sealed products
    print(f"\nSample of sealed products found (modified 2020+):")
    print("-" * 80)
    for i, product in enumerate(sealed_products[:5]):
        print(f"ID: {product['productId']} | Name: {product['name']} | Modified: {product['modifiedOn']} | Set: {product['set_code']}")
    
    if len(sealed_products) > 5:
        print(f"... and {len(sealed_products) - 5} more products")
else:
    print("\nNo sealed products found.")