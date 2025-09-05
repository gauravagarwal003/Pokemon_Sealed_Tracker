import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from datetime import datetime, timedelta
import glob

def get_available_dates():
    """
    Get all dates for which we have price data
    """
    price_files = glob.glob('daily_prices/market_prices_*.parquet')
    dates = [os.path.basename(f).replace('market_prices_', '').replace('.parquet', '') 
             for f in price_files]
    return sorted(dates)

def load_purchases():
    """
    Load purchase data from CSV
    """
    purchases_file = 'my_purchases.csv'
    if not os.path.exists(purchases_file):
        print("No purchases have been recorded yet. Please run track_purchases.py first.")
        return None
    
    purchases_df = pd.read_csv(purchases_file)
    if purchases_df.empty:
        print("No purchases have been recorded yet.")
        return None
    
    return purchases_df

def load_product_data():
    """
    Load product metadata
    """
    try:
        return pd.read_csv('sealed_products_tracking.csv')
    except FileNotFoundError:
        print("Error: sealed_products_tracking.csv not found.")
        return None

def calculate_collection_value(purchases_df, product_df, available_dates):
    """
    Calculate collection value over time, considering purchase dates
    """
    if purchases_df is None or product_df is None:
        return None
    
    # Convert purchase dates to datetime for comparison
    if 'dateReceived' in purchases_df.columns:
        purchases_df['dateReceived'] = pd.to_datetime(purchases_df['dateReceived'])
    elif 'purchase_date' in purchases_df.columns:
        # For backward compatibility with older data
        purchases_df['dateReceived'] = pd.to_datetime(purchases_df['purchase_date'])
    
    # Calculate spending over time (cumulative)
    purchases_df = purchases_df.sort_values('dateReceived')
    purchases_df['total_spent'] = purchases_df['quantity'] * purchases_df['purchase_price']
    
    # Create a dataframe to store daily values
    date_range = pd.to_datetime(available_dates)
    daily_values = pd.DataFrame(index=date_range)
    daily_values.index.name = 'date'
    daily_values['collection_value'] = 0.0
    daily_values['spent_to_date'] = 0.0
    
    # For each date, calculate collection value and spending
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        
        # Skip dates before first purchase
        if date < purchases_df['dateReceived'].min():
            continue
        
        # Load price data for this date
        try:
            price_file = f"daily_prices/market_prices_{date_str}.parquet"
            if not os.path.exists(price_file):
                # Use the closest previous date if this date's file doesn't exist
                previous_dates = [d for d in available_dates if d < date_str]
                if previous_dates:
                    latest_previous = max(previous_dates)
                    price_file = f"daily_prices/market_prices_{latest_previous}.parquet"
                else:
                    continue
            
            daily_prices = pd.read_parquet(price_file)
        except Exception as e:
            print(f"Error loading price data for {date_str}: {e}")
            continue
        
        # Calculate collection value for this date
        date_value = 0.0
        purchases_to_date = purchases_df[purchases_df['dateReceived'] <= date]
        
        # Track sold items
        sold_revenue = 0.0
        
        for _, purchase in purchases_to_date.iterrows():
            product_id = purchase['product_id']
            quantity = purchase['quantity']
            
            # Skip sold items for current value, but account for them in financial tracking
            if 'status' in purchase and purchase['status'] == 'SOLD':
                # For items sold before or on this date, add their sale value to revenue
                if 'sell_date' in purchase and pd.to_datetime(purchase['sell_date']) <= date:
                    if 'sell_price' in purchase:
                        sold_revenue += purchase['sell_price'] * quantity
                # Skip sold items for market value calculation
                continue
                
            # Get market price for this product
            product_price = daily_prices[daily_prices['productId'] == product_id]
            if not product_price.empty and pd.notna(product_price['marketPrice'].iloc[0]):
                market_price = product_price['marketPrice'].iloc[0]
                date_value += market_price * quantity
        
        # Calculate spending up to this date
        spent_to_date = purchases_to_date['total_spent'].sum()
        
        # Store values
        daily_values.loc[date, 'collection_value'] = date_value
        daily_values.loc[date, 'spent_to_date'] = spent_to_date
        daily_values.loc[date, 'sold_revenue'] = sold_revenue
    
    # Fill forward to handle missing dates
    daily_values = daily_values.fillna(method='ffill')
    
    # Calculate net investment (considering sales)
    daily_values['net_investment'] = daily_values['spent_to_date'] - daily_values['sold_revenue']
    
    # Calculate ROI
    daily_values['roi'] = ((daily_values['collection_value'] + daily_values['sold_revenue']) - 
                           daily_values['spent_to_date']) / daily_values['spent_to_date'] * 100
    
    return daily_values

def visualize_collection_value(daily_values):
    """
    Create visualizations of collection value over time
    """
    if daily_values is None or daily_values.empty:
        print("No data available for visualization.")
        return
    
    # Set up the figure
    plt.figure(figsize=(12, 10))
    
    # Plot 1: Collection Value vs. Amount Spent
    plt.subplot(2, 1, 1)
    plt.plot(daily_values.index, daily_values['collection_value'], 'b-', linewidth=2, label='Current Collection Value')
    plt.plot(daily_values.index, daily_values['spent_to_date'], 'r-', linewidth=2, label='Total Spent')
    plt.plot(daily_values.index, daily_values['net_investment'], 'r--', linewidth=2, label='Net Investment (After Sales)')
    
    if 'sold_revenue' in daily_values.columns and daily_values['sold_revenue'].max() > 0:
        plt.plot(daily_values.index, daily_values['sold_revenue'], 'g-', linewidth=2, label='Revenue from Sales')
    
    plt.fill_between(daily_values.index, 
                     daily_values['collection_value'] + daily_values['sold_revenue'], 
                     daily_values['spent_to_date'], 
                     where=((daily_values['collection_value'] + daily_values['sold_revenue']) >= daily_values['spent_to_date']),
                     color='green', alpha=0.3, label='Profit')
    plt.fill_between(daily_values.index, 
                     daily_values['collection_value'] + daily_values['sold_revenue'], 
                     daily_values['spent_to_date'], 
                     where=((daily_values['collection_value'] + daily_values['sold_revenue']) < daily_values['spent_to_date']),
                     color='red', alpha=0.3, label='Loss')
    
    plt.title('Pokémon Sealed Collection Value Over Time (Including Sold Items)', fontsize=16)
    plt.ylabel('USD ($)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Format the x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45)
    
    # Plot 2: ROI Percentage
    plt.subplot(2, 1, 2)
    plt.plot(daily_values.index, daily_values['roi'], 'g-', linewidth=2)
    plt.axhline(y=0, color='r', linestyle='-', alpha=0.5)
    plt.fill_between(daily_values.index, daily_values['roi'], 0, 
                     where=(daily_values['roi'] >= 0),
                     color='green', alpha=0.3)
    plt.fill_between(daily_values.index, daily_values['roi'], 0, 
                     where=(daily_values['roi'] < 0),
                     color='red', alpha=0.3)
    
    plt.title('Return on Investment (ROI) Percentage', fontsize=16)
    plt.ylabel('ROI (%)', fontsize=14)
    plt.grid(True, alpha=0.3)
    
    # Format the x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45)
    
    # Add summary stats as text
    last_value = daily_values.iloc[-1]
    total_value = last_value['collection_value'] + last_value['sold_revenue']
    net_investment = last_value['spent_to_date'] - last_value['sold_revenue']
    
    summary_text = f"Summary (as of {daily_values.index[-1].strftime('%Y-%m-%d')}):\n"
    summary_text += f"Current Collection Value: ${last_value['collection_value']:,.2f}\n"
    
    if last_value['sold_revenue'] > 0:
        summary_text += f"Revenue from Sold Items: ${last_value['sold_revenue']:,.2f}\n"
        summary_text += f"Total Value (Current + Sold): ${total_value:,.2f}\n"
    
    summary_text += f"Total Spent: ${last_value['spent_to_date']:,.2f}\n"
    
    if last_value['sold_revenue'] > 0:
        summary_text += f"Net Investment (After Sales): ${net_investment:,.2f}\n"
    
    profit_loss = total_value - last_value['spent_to_date']
    summary_text += f"Profit/Loss: ${profit_loss:,.2f}\n"
    summary_text += f"ROI: {last_value['roi']:.2f}%"
    
    plt.figtext(0.15, 0.01, summary_text, fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    
    # Save the figure
    plt.savefig('collection_value_over_time.png', dpi=300)
    print(f"Visualization saved as 'collection_value_over_time.png'")
    
    # Show the plot
    plt.show()

def main():
    """
    Main function to run the visualization
    """
    print("Loading data...")
    purchases_df = load_purchases()
    if purchases_df is None:
        return
    
    product_df = load_product_data()
    if product_df is None:
        return
    
    available_dates = get_available_dates()
    if not available_dates:
        print("No price data available. Please run daily_price_checker_parquet.py first.")
        return
    
    print(f"Found price data for {len(available_dates)} dates.")
    print(f"Date range: {min(available_dates)} to {max(available_dates)}")
    
    print("\nCalculating collection value over time...")
    daily_values = calculate_collection_value(purchases_df, product_df, available_dates)
    
    print("\nGenerating visualization...")
    visualize_collection_value(daily_values)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
