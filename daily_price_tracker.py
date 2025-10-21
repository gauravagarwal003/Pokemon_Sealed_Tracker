"""
Daily Pokemon Price Collector
Collects daily prices and triggers portfolio recompilation
Used by GitHub Actions for automated daily updates
"""

import pandas as pd
import requests
from io import StringIO
from datetime import datetime
try:
    # Python 3.9+ recommended
    from zoneinfo import ZoneInfo
    _PST_TZ = ZoneInfo('America/Los_Angeles')
except Exception:
    # Fallback to pytz if zoneinfo isn't available in the runtime
    try:
        import pytz
        _PST_TZ = pytz.timezone('America/Los_Angeles')
    except Exception:
        _PST_TZ = None
import os
import sys
import subprocess

def collect_daily_prices(force_update=False):
    """Collect current prices for all sealed products and save to Parquet format"""
    
    try:
        sealed_df = pd.read_csv('sealed_products_tracking.csv')
        print(f"Loaded sealed products tracking file with {len(sealed_df)} products")
        
        # Check if we have the new set code
        unique_sets = sorted(sealed_df['set_code'].unique())
        print(f"Tracking {len(unique_sets)} unique set codes: {unique_sets[-10:]}...")  # Show last 10
        
    except FileNotFoundError:
        print("ERROR: sealed_products_tracking.csv not found. Please run product_discovery.py first.")
        return False
    
    print(f"Checking market prices for {len(sealed_df)} sealed products...")
    
    # Create directory for daily price files
    os.makedirs('daily_prices', exist_ok=True)
    
    # Create a new DataFrame for today's market prices (Pacific Time)
    if _PST_TZ is not None:
        try:
            today_dt = datetime.now(_PST_TZ)
        except Exception:
            # Some pytz timezones require localize; fall back to naive now
            today_dt = datetime.now()
    else:
        today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    
    # Check if today's file already exists and skip if not forcing update
    parquet_filename = f"daily_prices/market_prices_{today}.parquet"
    if not force_update and os.path.exists(parquet_filename):
        print(f"Price file for {today} already exists. Use force_update=True to refresh.")
        return True
    
    price_records = []
    
    # Group products by set_code to minimize API calls
    set_codes = sealed_df['set_code'].unique()
    processed_count = 0
    successful_sets = 0
    
    for set_code in set_codes:
        print(f"Fetching prices for set {set_code}...")
        
        try:
            response = requests.get(f"https://tcgcsv.com/tcgplayer/3/{set_code}/ProductsAndPrices.csv", timeout=30)
            
            if response.status_code == 200:
                csv_data = StringIO(response.text)
                current_df = pd.read_csv(csv_data)
                # Ensure productId column is string to avoid mixed-type comparisons
                if 'productId' in current_df.columns:
                    current_df['productId'] = current_df['productId'].astype(str)
                
                # Filter for products modified in 2020 or later
                if 'modifiedOn' in current_df.columns:
                    current_df['modifiedOn'] = pd.to_datetime(current_df['modifiedOn'], errors='coerce')
                    current_df = current_df[current_df['modifiedOn'].dt.year >= 2020]
                
                # Get sealed products for this set
                set_products = sealed_df[sealed_df['set_code'] == set_code]
                
                for _, product in set_products.iterrows():
                    # Normalize product id to string
                    product_id = str(product['productId'])
                    
                    # Find current prices for this product
                    current_prices = current_df[current_df['productId'] == product_id]
                    
                    if not current_prices.empty:
                        current_price = current_prices.iloc[0]
                        market_price = current_price.get('marketPrice', None)
                        
                        # Convert to float, handle NaN/empty values
                        if pd.notna(market_price) and market_price != '':
                            try:
                                market_price = float(market_price)
                            except (ValueError, TypeError):
                                market_price = None
                        else:
                            market_price = None
                        
                        price_record = {
                            'productId': str(product_id),
                            'marketPrice': market_price
                        }
                    else:
                        # Product not found in current data
                        price_record = {
                            'productId': str(product_id),
                            'marketPrice': None
                        }
                    
                    price_records.append(price_record)
                    processed_count += 1
                
                successful_sets += 1
            else:
                print(f"HTTP {response.status_code} for set {set_code}")
                # Add records with None prices for products in this set
                set_products = sealed_df[sealed_df['set_code'] == set_code]
                for _, product in set_products.iterrows():
                    price_records.append({
                        'productId': str(product['productId']),
                        'marketPrice': None
                    })
                    processed_count += 1
                        
        except Exception as e:
            print(f"Error fetching data for set {set_code}: {e}")
            # Add records with None prices for products in this set
            set_products = sealed_df[sealed_df['set_code'] == set_code]
            for _, product in set_products.iterrows():
                price_records.append({
                    'productId': str(product['productId']),
                    'marketPrice': None
                })
                processed_count += 1
    
    if not price_records:
        print("ERROR: No price data could be retrieved")
        return False
    
    # Create DataFrame and save as Parquet
    price_df = pd.DataFrame(price_records)
    # Ensure productId is stored as string to avoid type mismatches later
    price_df['productId'] = price_df['productId'].astype(str)
    
    # Save daily Parquet file
    price_df.to_parquet(parquet_filename, engine='pyarrow', compression='snappy')
    print(f"Daily market prices saved to '{parquet_filename}'")
    
    # Show statistics
    valid_prices = price_df['marketPrice'].dropna()
    if len(valid_prices) > 0:
        print(f"\nPrice Statistics for {today}:")
        print(f"Successful set queries: {successful_sets} out of {len(set_codes)}")
        print(f"Products with market prices: {len(valid_prices)} out of {len(price_df)}")
        print(f"Average market price: ${valid_prices.mean():.2f}")
        print(f"Median market price: ${valid_prices.median():.2f}")
        print(f"Price range: ${valid_prices.min():.2f} - ${valid_prices.max():.2f}")
        
        file_size = os.path.getsize(parquet_filename)
        print(f"File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    else:
        print(f"No valid market prices found for {today}")
    
    print(f"Total products processed: {processed_count}")
    return True

def run_portfolio_recompiler():
    """Run the portfolio recompiler after collecting prices"""
    print("\nRunning portfolio recompiler...")
    try:
        result = subprocess.run([sys.executable, 'portfolio_recompiler.py'], 
                               capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("Portfolio recompiler completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"Portfolio recompiler failed with exit code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("Portfolio recompiler timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"Error running portfolio recompiler: {e}")
        return False

def main():
    """Main function for daily price collection and portfolio update"""
    print("=== Pokemon Daily Price Collection ===")
    # Print the current timestamp in Pacific Time when possible
    if _PST_TZ is not None:
        try:
            now_pst = datetime.now(_PST_TZ)
        except Exception:
            now_pst = datetime.now()
    else:
        now_pst = datetime.now()
    print(f"Date: {now_pst.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check for force update flag
    force_update = '--force' in sys.argv
    if force_update:
        print("Force update mode enabled - will refresh existing price files")
    
    # Step 1: Collect daily prices
    success = collect_daily_prices(force_update=force_update)
    if not success:
        print("Failed to collect daily prices")
        sys.exit(1)
    
    # Step 2: Run portfolio recompiler
    success = run_portfolio_recompiler()
    if not success:
        print("Portfolio recompiler failed, but prices were collected")
        sys.exit(1)
    
    # Show final summary
    today = datetime.now().strftime('%Y-%m-%d')
    parquet_file = f"daily_prices/market_prices_{today}.parquet"
    if os.path.exists(parquet_file):
        print(f"\n✅ Portfolio updated with prices from {today}")
        print(f"📊 Chart should now extend through {today}")
    else:
        print(f"\n⚠️ No price file created for {today}")
    
    print("\n=== Daily update completed successfully ===")

if __name__ == "__main__":
    main()