import pandas as pd
import requests
import subprocess
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def collect_historical_data():
    """
    Collect historical price data from TCGPlayer archives
    From 2024-02-08 to 2025-09-03 for sealed Pokemon products
    """
    
    # Load our sealed product IDs
    try:
        with open('sealed_product_ids.txt', 'r') as f:
            sealed_product_ids = set(int(line.strip()) for line in f if line.strip())
        print(f"Loaded {len(sealed_product_ids)} sealed product IDs")
    except FileNotFoundError:
        print("Error: sealed_product_ids.txt not found. Please run product_discovery.py first.")
        return
    
    # Load our set codes
    try:
        sealed_df = pd.read_csv('sealed_products_tracking.csv')
        set_codes = set(sealed_df['set_code'].unique())
        print(f"Loaded {len(set_codes)} set codes")
    except FileNotFoundError:
        print("Error: sealed_products_tracking.csv not found. Please run product_discovery.py first.")
        return
    
    # Create directory for daily price files
    if not os.path.exists('daily_prices'):
        os.makedirs('daily_prices')

    # Generate date range for missing dates (2025-09-21 to 2025-09-02)
    start_date = datetime(2025, 9, 6)
    end_date = datetime(2025, 9, 6)
    
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    processed_days = 0
    
    print(f"\nCollecting historical data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total days to process: {total_days}")
    print("=" * 60)
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        parquet_filename = f"daily_prices/market_prices_{date_str}.parquet"
        
        # Skip if we already have this date
        if os.path.exists(parquet_filename):
            print(f"✓ Skipping {date_str} - already exists")
            current_date += timedelta(days=1)
            processed_days += 1
            continue
        
        print(f"\n📅 Processing {date_str} ({processed_days + 1}/{total_days})")
        
        success = process_single_date(date_str, sealed_product_ids, set_codes)
        
        if success:
            print(f"✅ Successfully processed {date_str}")
        else:
            print(f"❌ Failed to process {date_str}")
        
        current_date += timedelta(days=1)
        processed_days += 1
        
        # Progress update every 10 days
        if processed_days % 10 == 0:
            progress_pct = (processed_days / total_days) * 100
            print(f"\n🔄 Progress: {processed_days}/{total_days} days ({progress_pct:.1f}%)")
    
    print(f"\n🎉 Historical data collection completed!")
    print(f"📊 Processed {processed_days} days of historical data")

def process_single_date(date_str, sealed_product_ids, set_codes):
    """
    Process a single date's archive
    """
    archive_url = f"https://tcgcsv.com/archive/tcgplayer/prices-{date_str}.ppmd.7z"
    archive_filename = f"prices-{date_str}.ppmd.7z"
    extracted_folder = date_str
    
    try:
        # Download archive
        print(f"  📥 Downloading {archive_filename}...")
        response = requests.get(archive_url, stream=True)
        
        if response.status_code != 200:
            print(f"  ❌ Archive not available for {date_str} (HTTP {response.status_code})")
            return False
        
        # Save archive
        with open(archive_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        archive_size = os.path.getsize(archive_filename) / (1024 * 1024)
        print(f"  📦 Downloaded {archive_filename} ({archive_size:.1f} MB)")
        
        # Extract archive
        print(f"  📂 Extracting archive...")
        result = subprocess.run(['7z', 'x', archive_filename, '-y'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  ❌ Failed to extract archive: {result.stderr}")
            cleanup_files(archive_filename, extracted_folder)
            return False
        
        # Process extracted data
        print(f"  🔍 Processing price data...")
        price_records = []
        
        # Look for Pokemon category (3) and our set codes
        pokemon_folder = Path(extracted_folder) / "3"
        if not pokemon_folder.exists():
            print(f"  ⚠️  No Pokemon data folder found for {date_str}")
            cleanup_files(archive_filename, extracted_folder)
            return False
        
        sets_found = 0
        products_found = 0
        
        for set_code in set_codes:
            set_folder = pokemon_folder / str(set_code)
            prices_file = set_folder / "prices"
            
            if prices_file.exists():
                sets_found += 1
                try:
                    # Read the prices file (JSON format)
                    import json
                    with open(prices_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract products from JSON structure
                    if 'results' in data and isinstance(data['results'], list):
                        for product in data['results']:
                            product_id = product.get('productId')
                            market_price = product.get('marketPrice')
                            
                            # Check if this is one of our sealed products
                            if product_id in sealed_product_ids:
                                # Convert to float, handle NaN/empty values
                                if market_price is not None and market_price != '':
                                    try:
                                        market_price = float(market_price)
                                    except (ValueError, TypeError):
                                        market_price = None
                                else:
                                    market_price = None
                                
                                price_records.append({
                                    'productId': int(product_id),
                                    'marketPrice': market_price
                                })
                                products_found += 1
                
                except Exception as e:
                    print(f"    ⚠️  Error processing set {set_code}: {e}")
                    continue
        
        print(f"  📊 Found {sets_found} sets, {products_found} product prices")
        
        # Save to Parquet if we have data
        if price_records:
            price_df = pd.DataFrame(price_records)
            
            # Remove duplicates (same product might appear multiple times)
            price_df = price_df.drop_duplicates(subset=['productId'])
            
            # Ensure productId is integer type
            price_df['productId'] = price_df['productId'].astype('int32')
            
            # Save to Parquet
            parquet_filename = f"daily_prices/market_prices_{date_str}.parquet"
            price_df.to_parquet(parquet_filename, engine='pyarrow', compression='snappy')
            
            file_size = os.path.getsize(parquet_filename) / 1024
            valid_prices = price_df['marketPrice'].dropna()
            print(f"  💾 Saved {len(price_df)} products ({len(valid_prices)} with prices) to {parquet_filename} ({file_size:.1f} KB)")
        else:
            print(f"  ⚠️  No price data found for our products on {date_str}")
        
        # Cleanup
        cleanup_files(archive_filename, extracted_folder)
        return True
        
    except Exception as e:
        print(f"  ❌ Error processing {date_str}: {e}")
        cleanup_files(archive_filename, extracted_folder)
        return False

def cleanup_files(archive_filename, extracted_folder):
    """
    Clean up downloaded and extracted files
    """
    try:
        if os.path.exists(archive_filename):
            os.remove(archive_filename)
        if os.path.exists(extracted_folder):
            shutil.rmtree(extracted_folder)
        print(f"  🧹 Cleaned up temporary files")
    except Exception as e:
        print(f"  ⚠️  Warning: Could not clean up files: {e}")

if __name__ == "__main__":
    collect_historical_data()
