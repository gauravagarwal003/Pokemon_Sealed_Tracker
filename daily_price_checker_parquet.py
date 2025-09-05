import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import os

def check_daily_prices_parquet():
    """
    Check current prices for all sealed products and save to Parquet format
    Stores only productId and marketPrice for efficient daily tracking
    """
    
    # Read the sealed products list
    try:
        sealed_df = pd.read_csv('sealed_products_tracking.csv')
    except FileNotFoundError:
        print("Error: sealed_products_tracking.csv not found. Please run the main script first.")
        return
    
    print(f"Checking market prices for {len(sealed_df)} sealed products...")
    
    # Create directory for daily price files
    if not os.path.exists('daily_prices'):
        os.makedirs('daily_prices')
    
    # Create a new DataFrame for today's market prices
    today = datetime.now().strftime("%Y-%m-%d")
    price_records = []
    
    # Group products by set_code to minimize API calls
    set_codes = sealed_df['set_code'].unique()
    processed_count = 0
    
    for set_code in set_codes:
        print(f"Fetching prices for set {set_code}...")
        
        try:
            response = requests.get(f"https://tcgcsv.com/tcgplayer/3/{set_code}/ProductsAndPrices.csv")
            
            if response.status_code == 200:
                csv_data = StringIO(response.text)
                current_df = pd.read_csv(csv_data)
                
                # Filter for products modified in 2020 or later (same as main script)
                if 'modifiedOn' in current_df.columns:
                    current_df['modifiedOn'] = pd.to_datetime(current_df['modifiedOn'], errors='coerce')
                    current_df = current_df[current_df['modifiedOn'].dt.year >= 2020]
                
                # Get sealed products for this set
                set_products = sealed_df[sealed_df['set_code'] == set_code]
                
                for _, product in set_products.iterrows():
                    product_id = product['productId']
                    
                    # Find current prices for this product
                    current_prices = current_df[current_df['productId'] == product_id]
                    
                    if not current_prices.empty:
                        # Get the market price
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
                            'productId': int(product_id),
                            'marketPrice': market_price
                        }
                    else:
                        # Product not found in current data
                        price_record = {
                            'productId': int(product_id),
                            'marketPrice': None
                        }
                    
                    price_records.append(price_record)
                    processed_count += 1
                        
        except Exception as e:
            print(f"Error fetching data for set {set_code}: {e}")
            # Add records with None prices for products in this set
            set_products = sealed_df[sealed_df['set_code'] == set_code]
            for _, product in set_products.iterrows():
                price_records.append({
                    'productId': int(product['productId']),
                    'marketPrice': None
                })
                processed_count += 1
            continue
    
    if price_records:
        # Create DataFrame and save as Parquet
        price_df = pd.DataFrame(price_records)
        
        # Ensure productId is integer type
        price_df['productId'] = price_df['productId'].astype('int32')
        
        # Save daily Parquet file
        parquet_filename = f"daily_prices/market_prices_{today}.parquet"
        price_df.to_parquet(parquet_filename, engine='pyarrow', compression='snappy')
        print(f"\nDaily market prices saved to '{parquet_filename}'")
        
        # Show statistics
        valid_prices = price_df['marketPrice'].dropna()
        if len(valid_prices) > 0:
            print(f"\nPrice Statistics for {today}:")
            print(f"Products with market prices: {len(valid_prices)} out of {len(price_df)}")
            print(f"Average market price: ${valid_prices.mean():.2f}")
            print(f"Median market price: ${valid_prices.median():.2f}")
            print(f"Highest market price: ${valid_prices.max():.2f}")
            print(f"Lowest market price: ${valid_prices.min():.2f}")
            
            # Show file size
            file_size = os.path.getsize(parquet_filename)
            print(f"File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            print(f"No valid market prices found for {today}")
        
        print(f"Total products processed: {processed_count}")
        
        # Create/update master price history (optional - for easy access to all data)
        update_master_history(price_df, today)
        
    else:
        print("No price data could be retrieved.")

def update_master_history(daily_df, date):
    """
    Optionally maintain a master Parquet file with all historical data
    """
    master_file = "all_market_prices.parquet"
    
    # Add date column to daily data
    daily_df = daily_df.copy()
    daily_df['date'] = date
    
    # Reorder columns
    daily_df = daily_df[['date', 'productId', 'marketPrice']]
    
    if os.path.exists(master_file):
        # Append to existing master file
        try:
            existing_df = pd.read_parquet(master_file)
            # Remove today's data if it already exists (for reruns)
            existing_df = existing_df[existing_df['date'] != date]
            # Combine with new data
            combined_df = pd.concat([existing_df, daily_df], ignore_index=True)
            combined_df.to_parquet(master_file, engine='pyarrow', compression='snappy')
            print(f"Master history file updated: {master_file}")
        except Exception as e:
            print(f"Warning: Could not update master file: {e}")
    else:
        # Create new master file
        daily_df.to_parquet(master_file, engine='pyarrow', compression='snappy')
        print(f"Master history file created: {master_file}")

def read_daily_prices(date):
    """
    Helper function to read prices for a specific date
    """
    filename = f"daily_prices/market_prices_{date}.parquet"
    if os.path.exists(filename):
        return pd.read_parquet(filename)
    else:
        print(f"No price data found for {date}")
        return None

def read_all_prices():
    """
    Helper function to read all historical price data
    """
    master_file = "all_market_prices.parquet"
    if os.path.exists(master_file):
        return pd.read_parquet(master_file)
    else:
        print("No master price history found")
        return None

if __name__ == "__main__":
    check_daily_prices_parquet()
