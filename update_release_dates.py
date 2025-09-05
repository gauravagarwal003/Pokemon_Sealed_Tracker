#!/usr/bin/env python3
"""
Script to update sealed_products_tracking.csv by replacing modifiedOn with earliestDate
from TCG API presaleInfo.releasedOn field
"""

import requests
import pandas as pd
import json
from datetime import datetime
import time

def get_all_products_with_release_dates():
    """
    Get all products with their release dates using the groups/products API
    """
    pokemon_category = '3'
    product_release_dates = {}
    
    print("Fetching all groups...")
    r = requests.get(f"https://tcgcsv.com/tcgplayer/{pokemon_category}/groups")
    all_groups = r.json()['results']
    
    print(f"Found {len(all_groups)} groups. Fetching products...")
    
    for i, group in enumerate(all_groups):
        group_id = group['groupId']
        group_name = group.get('name', f'Group {group_id}')
        print(f"Processing group {i+1}/{len(all_groups)}: {group_name}")
        
        try:
            r = requests.get(f"https://tcgcsv.com/tcgplayer/{pokemon_category}/{group_id}/products")
            products = r.json()['results']
            
            for product in products:
                product_id = product.get('productId')
                if product_id and 'presaleInfo' in product and product['presaleInfo']:
                    released_on = product['presaleInfo'].get('releasedOn')
                    if released_on:
                        try:
                            # Handle different date formats
                            if 'T' in released_on:
                                date_obj = datetime.fromisoformat(released_on.replace('Z', '+00:00'))
                            else:
                                date_obj = datetime.strptime(released_on, '%Y-%m-%d')
                            product_release_dates[product_id] = date_obj.strftime('%Y-%m-%d')
                        except Exception as e:
                            print(f"Warning: Could not parse date {released_on} for product {product_id}: {e}")
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error fetching products for group {group_id}: {e}")
            continue
    
    print(f"Found release dates for {len(product_release_dates)} products")
    return product_release_dates

def update_csv_with_release_dates():
    """
    Update the CSV file by replacing modifiedOn with earliestDate
    """
    csv_file = '/Users/gaurav/Downloads/Projects/Pokemon/PokemonSealedPriceTeacker/sealed_products_tracking.csv'
    
    # Read the current CSV
    print("Reading current CSV file...")
    df = pd.read_csv(csv_file)
    
    print(f"Found {len(df)} products to update")
    
    # Get all products with release dates
    product_release_dates = get_all_products_with_release_dates()
    
    # Create a new column for release dates
    df['earliestDate'] = None
    
    # Update release dates for products we found
    for index, row in df.iterrows():
        product_id = row['productId']
        if product_id in product_release_dates:
            df.at[index, 'earliestDate'] = product_release_dates[product_id]
            print(f"Updated product {product_id} with release date {product_release_dates[product_id]}")
        else:
            print(f"No release date found for product {product_id}")
    
    # Remove the modifiedOn column and reorder columns
    columns = ['productId', 'name', 'cleanName', 'imageUrl', 'earliestDate', 'set_code', 'url']
    df = df[columns]
    
    # Save the updated CSV
    backup_file = csv_file.replace('.csv', '_backup.csv')
    print(f"Creating backup at {backup_file}")
    pd.read_csv(csv_file).to_csv(backup_file, index=False)
    
    print(f"Saving updated CSV to {csv_file}")
    df.to_csv(csv_file, index=False)
    
    # Print summary
    valid_dates = df['earliestDate'].notna().sum()
    print(f"\nSummary:")
    print(f"Total products: {len(df)}")
    print(f"Products with release dates: {valid_dates}")
    print(f"Products without release dates: {len(df) - valid_dates}")

if __name__ == "__main__":
    print("Starting CSV update process...")
    update_csv_with_release_dates()
    print("Process completed!")
