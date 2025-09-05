#!/usr/bin/env python3
import pandas as pd
from datetime import datetime

def update_my_purchases():
    """
    Update my_purchases.csv to:
    1. Rename purchase_date to dateReceived
    2. Ensure dateReceived is the later of purchase_date and earliestDate for each product
    """
    print("Reading my_purchases.csv and sealed_products_tracking.csv...")
    
    # Read the purchases file
    purchases_file = 'my_purchases.csv'
    try:
        purchases_df = pd.read_csv(purchases_file)
    except FileNotFoundError:
        print("Error: my_purchases.csv not found.")
        return
    
    # Read the products file
    products_file = 'sealed_products_tracking.csv'
    try:
        products_df = pd.read_csv(products_file)
    except FileNotFoundError:
        print("Error: sealed_products_tracking.csv not found.")
        return
    
    print(f"Found {len(purchases_df)} purchases to update.")
    
    # Rename purchase_date to dateReceived (store original values)
    if 'purchase_date' in purchases_df.columns:
        purchases_df = purchases_df.rename(columns={'purchase_date': 'dateReceived'})
    else:
        print("Warning: 'purchase_date' column not found. Creating 'dateReceived' column.")
        purchases_df['dateReceived'] = None
    
    # Make sure productId column matches between the two files
    products_df['productId'] = products_df['productId'].astype(str)
    purchases_df['product_id'] = purchases_df['product_id'].astype(str)
    
    # Create a dictionary of earliestDates from products_df
    earliest_dates = {}
    for _, row in products_df.iterrows():
        product_id = row['productId']
        if pd.notna(row['earliestDate']):
            earliest_dates[product_id] = row['earliestDate']
    
    print(f"Found earliestDate for {len(earliest_dates)} products.")
    
    # Update dateReceived to be the later of purchase_date and earliestDate
    updated_count = 0
    for idx, row in purchases_df.iterrows():
        product_id = row['product_id']
        
        # Convert dateReceived to datetime for comparison
        date_received = pd.to_datetime(row['dateReceived'])
        
        # Get earliestDate for this product
        if product_id in earliest_dates:
            earliest_date = pd.to_datetime(earliest_dates[product_id])
            
            # Set dateReceived to the later of the two dates
            if earliest_date > date_received:
                purchases_df.at[idx, 'dateReceived'] = earliest_date.strftime('%Y-%m-%d')
                updated_count += 1
    
    print(f"Updated dateReceived for {updated_count} out of {len(purchases_df)} purchases.")
    
    # Save the updated DataFrame back to CSV
    purchases_df.to_csv(purchases_file, index=False)
    print(f"Updated CSV saved to {purchases_file}")

if __name__ == "__main__":
    update_my_purchases()
