# Pokemon Sealed Product Collection Tracker

This extension allows you to track your Pokémon sealed product purchases and visualize the value of your collection over time.

## Getting Started

1. Make sure you have installed the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Track your purchases:
   ```
   python track_purchases.py
   ```

3. Visualize your collection's value over time:
   ```
   python visualize_collection.py
   ```

## Features

- **Track your purchases**: Record what you bought, when you bought it, and how much you paid
- **Fuzzy search for products**: Find products by name even with partial or approximate matches
- **Open products in your collection**: Mark products as opened while still tracking their value
- **Sell products**: Record sales of items from your collection with selling prices and dates
- **View purchase history**: See a summary of your collection purchases
- **Visualize collection value**: Generate graphs showing your collection's value over time
- **ROI tracking**: See the return on investment for your collection, including sold items

## How It Works

The system uses the daily price data that's already being collected to calculate your collection's value at each point in time. It accounts for purchases made at different dates, showing a realistic view of your spending and collection value over time.

### Collection Status Tracking

Products in your collection can have one of three states:
- **Active** (default): Sealed products in your collection
- **Opened**: Products you've opened but still own
- **Sold**: Products you've sold, with tracking of the sale price and date

### Financial Tracking

The visualization shows:
1. Your collection's current market value over time
2. The total amount you've spent over time (accounting for when purchases were made)
3. Revenue from sold items over time
4. Net investment (total spent minus revenue from sales)
5. Profit/loss (the difference between total value and amount spent)
6. Return on Investment (ROI) percentage

## Files

- `track_purchases.py`: Tool for recording and managing your purchases
- `visualize_collection.py`: Tool for visualizing your collection's value over time
- `my_purchases.csv`: Database of your purchases (created when you add your first purchase)
- `collection_value_over_time.png`: Generated graph of your collection's value

Happy collecting!
