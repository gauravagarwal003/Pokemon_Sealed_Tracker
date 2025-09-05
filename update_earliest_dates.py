#!/usr/bin/env python3
import pandas as pd
import os
import re
from datetime import datetime

def update_earliest_dates():
    """
    Update sealed_products_tracking.csv:
    1. Rename releaseDate column to earliestDate
    2. Populate earliestDate with the earliest date a product has a price in any parquet file
    """
    print("Reading sealed_products_tracking.csv...")
    
    # Read the CSV file
    csv_path = 'sealed_products_tracking.csv'
    products_df = pd.read_csv(csv_path)
    
    # Check if the column exists before renaming
    if 'releaseDate' in products_df.columns:
        # Rename releaseDate to earliestDate
        products_df = products_df.rename(columns={'releaseDate': 'earliestDate'})
    else:
        print("Warning: 'releaseDate' column not found. Creating 'earliestDate' column.")
        products_df['earliestDate'] = None
    
    # Get all product IDs
    product_ids = products_df['productId'].unique()
    print(f"Found {len(product_ids)} unique products.")
    
    # Get a list of all parquet files sorted by date
    parquet_dir = 'daily_prices'
    parquet_files = []
    
    for filename in os.listdir(parquet_dir):
        if filename.endswith('.parquet') and filename.startswith('market_prices_'):
            # Extract date from filename using regex
            match = re.search(r'market_prices_(\d{4}-\d{2}-\d{2})\.parquet', filename)
            if match:
                date_str = match.group(1)
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                parquet_files.append((date_obj, os.path.join(parquet_dir, filename)))
    
    # Sort files by date (oldest first)
    parquet_files.sort(key=lambda x: x[0])
    
    if not parquet_files:
        print("No parquet files found.")
        return
    
    print(f"Found {len(parquet_files)} parquet files.")
    
    # Dictionary to track earliest date for each product
    earliest_dates = {}
    
    # Process each parquet file
    for date_obj, parquet_path in parquet_files:
        date_str = date_obj.strftime('%Y-%m-%d')
        try:
            # Read the parquet file
            price_df = pd.read_parquet(parquet_path)
            
            # Ensure productId is integer type
            price_df['productId'] = price_df['productId'].astype('int64')
            
            # For each product in this file with a non-null price
            valid_prices = price_df[pd.notna(price_df['marketPrice'])]
            for product_id in valid_prices['productId']:
                # Only record the date if it's the first occurrence for this product
                if product_id not in earliest_dates:
                    earliest_dates[product_id] = date_str
        except Exception as e:
            print(f"Error processing {parquet_path}: {e}")
    
    # Update the earliestDate column in the DataFrame
    updated_count = 0
    for idx, row in products_df.iterrows():
        product_id = row['productId']
        if product_id in earliest_dates:
            products_df.at[idx, 'earliestDate'] = earliest_dates[product_id]
            updated_count += 1
    
    print(f"Updated earliestDate for {updated_count} out of {len(products_df)} products.")
    
    # Save the updated DataFrame back to CSV
    products_df.to_csv(csv_path, index=False)
    print(f"Updated CSV saved to {csv_path}")

if __name__ == "__main__":
    update_earliest_dates()
