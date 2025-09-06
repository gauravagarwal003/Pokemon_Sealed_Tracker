import pandas as pd
import os
from datetime import datetime
import re
from thefuzz import process, fuzz

def get_inventory_summary():
    """
    Get a summary of current inventory by product, showing available quantities
    """
    purchases_file = 'my_purchases.csv'
    if not os.path.exists(purchases_file):
        return pd.DataFrame()
    
    purchases_df = pd.read_csv(purchases_file)
    if purchases_df.empty:
        return pd.DataFrame()
    
    # Group by product and calculate available quantities
    inventory = []
    
    for product_id in purchases_df['product_id'].unique():
        product_purchases = purchases_df[purchases_df['product_id'] == product_id]
        product_name = product_purchases['product_name'].iloc[0]
        
        total_purchased = product_purchases['quantity'].sum()
        
        # Calculate sold quantities
        sold_qty = 0
        if 'status' in product_purchases.columns and 'quantity' in product_purchases.columns:
            sold_items = product_purchases[product_purchases['status'] == 'SOLD']
            sold_qty = sold_items['quantity'].sum()
        
        # Calculate opened quantities (still in collection but opened)
        opened_qty = 0
        if 'status' in product_purchases.columns:
            opened_items = product_purchases[product_purchases['status'] == 'OPENED']
            opened_qty = opened_items['quantity'].sum()
        
        # Available quantity (sealed items)
        sealed_qty = total_purchased - sold_qty - opened_qty
        
        inventory.append({
            'product_id': product_id,
            'product_name': product_name,
            'total_purchased': total_purchased,
            'sealed_available': sealed_qty,
            'opened_quantity': opened_qty,
            'sold_quantity': sold_qty
        })
    
    return pd.DataFrame(inventory)

def get_available_quantity(product_id, include_opened=False):
    """
    Get the available quantity for a specific product
    
    Args:
        product_id: The product ID to check
        include_opened: Whether to include opened items in the count
    
    Returns:
        int: Available quantity
    """
    inventory = get_inventory_summary()
    if inventory.empty:
        return 0
    
    product_inventory = inventory[inventory['product_id'] == product_id]
    if product_inventory.empty:
        return 0
    
    available = product_inventory['sealed_available'].iloc[0]
    if include_opened:
        available += product_inventory['opened_quantity'].iloc[0]
    
    return available

def search_products(search_term):
    """
    Search for products in the tracking list by name using fuzzy matching
    """
    try:
        sealed_df = pd.read_csv('sealed_products_tracking.csv')
    except FileNotFoundError:
        print("Error: sealed_products_tracking.csv not found.")
        return pd.DataFrame()
    
    # First try direct substring match (case-insensitive)
    pattern = re.compile(search_term, re.IGNORECASE)
    direct_matches = sealed_df[sealed_df['cleanName'].apply(lambda x: bool(pattern.search(str(x))))]
    
    # If we have direct matches, return them
    if not direct_matches.empty:
        return direct_matches
    
    # Otherwise, use fuzzy matching
    # Get list of all product names
    product_names = sealed_df['cleanName'].tolist()
    
    # Find top 10 fuzzy matches
    fuzzy_matches = process.extract(search_term, product_names, 
                                   scorer=fuzz.token_sort_ratio, 
                                   limit=10)
    
    # Only keep matches with score above 60
    good_matches = [name for name, score in fuzzy_matches if score > 60]
    
    # Return matching products
    if good_matches:
        return sealed_df[sealed_df['cleanName'].isin(good_matches)]
    
    return pd.DataFrame()

def format_product_list(products_df):
    """
    Format products for display
    """
    if products_df.empty:
        return "No products found matching your search."
    
    formatted = "Found the following products:\n"
    for i, (_, product) in enumerate(products_df.iterrows(), 1):
        formatted += f"{i}. {product['cleanName']} (ID: {product['productId']})\n"
    
    return formatted

def add_purchase():
    """
    Add a new purchase to the tracking system
    """
    # Create purchases file if it doesn't exist
    purchases_file = 'my_purchases.csv'
    if not os.path.exists(purchases_file):
        purchases_df = pd.DataFrame(columns=[
            'product_id', 'product_name', 'quantity', 'purchase_price', 'dateReceived'
        ])
        purchases_df.to_csv(purchases_file, index=False)
    else:
        purchases_df = pd.read_csv(purchases_file)
    
    # Search for product
    search_term = input("Enter product name to search: ")
    matching_products = search_products(search_term)
    
    print(format_product_list(matching_products))
    
    if matching_products.empty:
        print("No products found. Try a different search term.")
        return
    
    # Select product
    selection = input("Enter the number of the product you purchased (or 0 to cancel): ")
    try:
        selection_idx = int(selection) - 1
        if selection_idx < 0:
            print("Purchase cancelled.")
            return
        
        selected_product = matching_products.iloc[selection_idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return
    
    # Get purchase details
    try:
        quantity = int(input(f"How many {selected_product['cleanName']} did you purchase? "))
        if quantity <= 0:
            print("Quantity must be greater than 0.")
            return
        
        unit_price = float(input("What was the purchase price per item? $"))
        if unit_price <= 0:
            print("Price must be greater than 0.")
            return
        
        date_input = input("When did you make the purchase? (YYYY-MM-DD, leave blank for today): ")
        if date_input:
            purchase_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            purchase_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get the earliestDate for the product
        try:
            product_df = pd.read_csv('sealed_products_tracking.csv')
            product_info = product_df[product_df['productId'] == selected_product['productId']]
            earliest_date = None
            
            if not product_info.empty and 'earliestDate' in product_info.columns:
                earliest_date_str = product_info['earliestDate'].iloc[0]
                if pd.notna(earliest_date_str):
                    earliest_date = earliest_date_str
            
            # dateReceived should be the later of purchase_date and earliestDate
            dateReceived = purchase_date
            if earliest_date is not None:
                if pd.to_datetime(earliest_date) > pd.to_datetime(purchase_date):
                    dateReceived = earliest_date
                    print(f"Note: Setting dateReceived to {dateReceived} (earliestDate) as it's later than purchase date")
                
        except Exception as e:
            print(f"Warning: Could not check earliestDate: {e}")
            dateReceived = purchase_date
        
        # Record the purchase
        new_purchase = {
            'product_id': selected_product['productId'],
            'product_name': selected_product['cleanName'],
            'quantity': quantity,
            'purchase_price': unit_price,
            'dateReceived': dateReceived
        }
        
        purchases_df = pd.concat([purchases_df, pd.DataFrame([new_purchase])], ignore_index=True)
        purchases_df.to_csv(purchases_file, index=False)
        
        print(f"\nPurchase recorded successfully!")
        print(f"Added {quantity} x {selected_product['cleanName']} at ${unit_price:.2f} each (${quantity * unit_price:.2f} total)")
        print(f"Purchase date: {purchase_date}")
        print(f"Date received: {dateReceived}")
        
    except ValueError as e:
        print(f"Error: {e}")
        return

def view_purchases():
    """
    View all recorded purchases
    """
    purchases_file = 'my_purchases.csv'
    if not os.path.exists(purchases_file):
        print("No purchases have been recorded yet.")
        return
    
    purchases_df = pd.read_csv(purchases_file)
    
    if purchases_df.empty:
        print("No purchases have been recorded yet.")
        return
    
    # Calculate totals
    purchases_df['total_cost'] = purchases_df['quantity'] * purchases_df['purchase_price']
    
    # Sort by date
    if 'dateReceived' in purchases_df.columns:
        purchases_df = purchases_df.sort_values('dateReceived')
    
    # Display purchases
    print("\n===== YOUR COLLECTION PURCHASES =====")
    for idx, purchase in purchases_df.iterrows():
        status = ""
        if 'status' in purchase and purchase['status']:
            status = f" [{purchase['status']}]"
        
        # Use dateReceived if available, otherwise fall back to purchase_date
        date_col = 'dateReceived' if 'dateReceived' in purchase else 'purchase_date'
        display_date = purchase.get(date_col, 'Unknown')
            
        print(f"{idx+1}. {display_date} - {purchase['quantity']} x {purchase['product_name']}{status}")
        print(f"   Price: ${purchase['purchase_price']:.2f} each, Total: ${purchase['total_cost']:.2f}")
    
    # Show overall stats
    # Check if status column exists before filtering
    if 'status' in purchases_df.columns:
        sealed_purchases = purchases_df[purchases_df['status'].isna() | (purchases_df['status'] == '')]
        opened_purchases = purchases_df[purchases_df['status'] == 'OPENED']
        sold_purchases = purchases_df[purchases_df['status'] == 'SOLD']
    else:
        # If no status column, assume all purchases are sealed
        sealed_purchases = purchases_df.copy()
        opened_purchases = pd.DataFrame()
        sold_purchases = pd.DataFrame()
    
    sealed_items = sealed_purchases['quantity'].sum() if not sealed_purchases.empty else 0
    opened_items = opened_purchases['quantity'].sum() if not opened_purchases.empty else 0
    sold_items = sold_purchases['quantity'].sum() if not sold_purchases.empty else 0
    
    sealed_cost = sealed_purchases['total_cost'].sum() if not sealed_purchases.empty else 0
    opened_cost = opened_purchases['total_cost'].sum() if not opened_purchases.empty else 0
    
    # Calculate revenue from sold items
    sold_revenue = 0
    if 'sell_price' in purchases_df.columns and 'sell_date' in purchases_df.columns and not sold_purchases.empty:
        sold_revenue = (sold_purchases['quantity'] * sold_purchases['sell_price']).sum()
    
    print("\n===== COLLECTION SUMMARY =====")
    print(f"Sealed items (market value): {sealed_items} items, Cost: ${sealed_cost:.2f}")
    if opened_items > 0:
        print(f"Opened items (no market value): {opened_items} items, Cost: ${opened_cost:.2f}")
    if sold_items > 0:
        print(f"Sold items: {sold_items} items, Revenue: ${sold_revenue:.2f}")
    
    total_owned = sealed_items + opened_items
    total_cost_owned = sealed_cost + opened_cost
    
    print(f"\nTotal items owned: {total_owned}")
    print(f"Total cost of owned items: ${total_cost_owned:.2f}")
    if total_owned > 0:
        print(f"Average cost per owned item: ${total_cost_owned / total_owned:.2f}")
    
    if sold_revenue > 0:
        print(f"\nNote: Only sealed items contribute to collection market value.")
        print(f"Opened items retain their purchase cost but have no resale value.")
        
    return purchases_df

def view_inventory():
    """
    Display current inventory summary
    """
    inventory = get_inventory_summary()
    
    if inventory.empty:
        print("No inventory found.")
        return
    
    # Filter to show only products with any quantity (purchased, opened, or sold)
    inventory = inventory[inventory['total_purchased'] > 0]
    
    if inventory.empty:
        print("No products in inventory.")
        return
    
    print("\n" + "="*80)
    print("CURRENT INVENTORY SUMMARY")
    print("="*80)
    print(f"{'#':<3} {'Product Name':<40} {'Sealed':<8} {'Opened':<8} {'Sold':<6} {'Total':<6}")
    print(f"{'':3} {'(has market value)':<40} {'':8} {'(no market value)':<15} {'':6} {'':6}")
    print("-"*80)
    
    total_sealed = 0
    total_opened = 0
    total_sold = 0
    
    for idx, item in inventory.iterrows():
        sealed = int(item['sealed_available'])
        opened = int(item['opened_quantity'])
        sold = int(item['sold_quantity'])
        total = int(item['total_purchased'])
        
        total_sealed += sealed
        total_opened += opened
        total_sold += sold
        
        # Truncate long product names
        name = item['product_name']
        if len(name) > 38:
            name = name[:35] + "..."
        
        print(f"{idx+1:<3} {name:<40} {sealed:<8} {opened:<8} {sold:<6} {total:<6}")
    
    print("-"*80)
    print(f"{'TOTALS':<44} {total_sealed:<8} {total_opened:<8} {total_sold:<6} {total_sealed+total_opened+total_sold:<6}")
    print("="*80)
    
    return inventory

def open_product():
    """
    Mark products as opened in your collection with quantity validation
    """
    inventory = view_inventory()
    if inventory is None or inventory.empty:
        return
    
    # Filter to show only products with sealed quantities
    sealed_inventory = inventory[inventory['sealed_available'] > 0]
    
    if sealed_inventory.empty:
        print("No sealed products available to open.")
        return
    
    print("\nProducts available to open (sealed only):")
    print(f"{'#':<3} {'Product Name':<40} {'Available':<9}")
    print("-"*55)
    
    for idx, item in sealed_inventory.iterrows():
        name = item['product_name']
        if len(name) > 38:
            name = name[:35] + "..."
        print(f"{idx+1:<3} {name:<40} {int(item['sealed_available']):<9}")
    
    # Select which product to open
    selection = input("\nEnter the number of the product you want to open (or 0 to cancel): ")
    try:
        selection_idx = int(selection) - 1
        if selection_idx < 0:
            print("Operation cancelled.")
            return
        
        selected_item = sealed_inventory.iloc[selection_idx]
        product_id = selected_item['product_id']
        product_name = selected_item['product_name']
        available_qty = int(selected_item['sealed_available'])
        
    except (ValueError, IndexError):
        print("Invalid selection.")
        return
    
    # Get quantity to open
    try:
        if available_qty == 1:
            quantity_to_open = 1
            print(f"Opening 1 x {product_name}")
        else:
            quantity_to_open = int(input(f"How many {product_name} do you want to open? (1-{available_qty}): "))
            
        if quantity_to_open <= 0 or quantity_to_open > available_qty:
            print(f"Invalid quantity. You have {available_qty} sealed items available.")
            return
            
    except ValueError:
        print("Invalid quantity entered.")
        return
    
    # Confirm
    confirm = input(f"Are you sure you want to mark {quantity_to_open} x {product_name} as OPENED? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Process the opening by updating purchase records
    purchases_df = pd.read_csv('my_purchases.csv')
    
    # Find sealed items for this product (oldest first for FIFO)
    product_purchases = purchases_df[purchases_df['product_id'] == product_id].copy()
    
    # Add default status column if it doesn't exist
    if 'status' not in purchases_df.columns:
        purchases_df['status'] = None
    
    remaining_to_open = quantity_to_open
    
    for idx, purchase in product_purchases.iterrows():
        if remaining_to_open <= 0:
            break
            
        # Skip already sold or opened items
        current_status = purchase.get('status')
        if current_status in ['SOLD', 'OPENED']:
            continue
            
        purchase_qty = purchase['quantity']
        
        if remaining_to_open >= purchase_qty:
            # Open entire purchase
            purchases_df.at[idx, 'status'] = 'OPENED'
            remaining_to_open -= purchase_qty
        else:
            # Split purchase - need to create new records
            # Keep original as sealed with reduced quantity
            purchases_df.at[idx, 'quantity'] = purchase_qty - remaining_to_open
            
            # Create new record for opened portion
            opened_record = purchase.copy()
            opened_record['quantity'] = remaining_to_open
            opened_record['status'] = 'OPENED'
            
            purchases_df = pd.concat([purchases_df, pd.DataFrame([opened_record])], ignore_index=True)
            remaining_to_open = 0
    
    # Save the updated DataFrame
    purchases_df.to_csv('my_purchases.csv', index=False)
    
    print(f"\n{quantity_to_open} x {product_name} has been marked as OPENED.")
    print("⚠️  Important: Opened items are removed from your collection's market value.")
    print("   They retain their purchase cost but have no resale value in tracking.")

def sell_product():
    """
    Sell products from your collection with quantity validation
    """
    inventory = view_inventory()
    if inventory is None or inventory.empty:
        return
    
    # Filter to show only products with available quantities (sealed + opened)
    available_inventory = inventory[(inventory['sealed_available'] > 0) | (inventory['opened_quantity'] > 0)]
    
    if available_inventory.empty:
        print("No products available to sell.")
        return
    
    print("\nProducts available to sell:")
    print(f"{'#':<3} {'Product Name':<40} {'Sealed':<8} {'Opened':<8} {'Total':<6}")
    print("-"*70)
    
    for idx, item in available_inventory.iterrows():
        name = item['product_name']
        if len(name) > 38:
            name = name[:35] + "..."
        sealed = int(item['sealed_available'])
        opened = int(item['opened_quantity'])
        total = sealed + opened
        print(f"{idx+1:<3} {name:<40} {sealed:<8} {opened:<8} {total:<6}")
    
    # Select which product to sell
    selection = input("\nEnter the number of the product you want to sell (or 0 to cancel): ")
    try:
        selection_idx = int(selection) - 1
        if selection_idx < 0:
            print("Operation cancelled.")
            return
        
        selected_item = available_inventory.iloc[selection_idx]
        product_id = selected_item['product_id']
        product_name = selected_item['product_name']
        sealed_qty = int(selected_item['sealed_available'])
        opened_qty = int(selected_item['opened_quantity'])
        total_available = sealed_qty + opened_qty
        
    except (ValueError, IndexError):
        print("Invalid selection.")
        return
    
    # Get quantity to sell
    try:
        if total_available == 1:
            quantity_to_sell = 1
            print(f"Selling 1 x {product_name}")
        else:
            quantity_to_sell = int(input(f"How many {product_name} do you want to sell? (1-{total_available}): "))
            
        if quantity_to_sell <= 0 or quantity_to_sell > total_available:
            print(f"Invalid quantity. You have {total_available} items available ({sealed_qty} sealed + {opened_qty} opened).")
            return
            
    except ValueError:
        print("Invalid quantity entered.")
        return
    
    # Get selling details
    try:
        sell_price = float(input("What price did you sell each item for? $"))
        if sell_price <= 0:
            print("Price must be greater than 0.")
            return
        
        date_input = input("When did you sell it? (YYYY-MM-DD, leave blank for today): ")
        if date_input:
            sell_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            sell_date = datetime.now().strftime("%Y-%m-%d")
        
        # Calculate average purchase price for this product
        purchases_df = pd.read_csv('my_purchases.csv')
        product_purchases = purchases_df[purchases_df['product_id'] == product_id]
        
        # Exclude already sold items from cost calculation
        if 'status' in product_purchases.columns:
            unsold_purchases = product_purchases[product_purchases['status'] != 'SOLD']
        else:
            unsold_purchases = product_purchases
        
        if not unsold_purchases.empty:
            total_cost = (unsold_purchases['quantity'] * unsold_purchases['purchase_price']).sum()
            total_qty = unsold_purchases['quantity'].sum()
            avg_purchase_price = total_cost / total_qty if total_qty > 0 else 0
        else:
            avg_purchase_price = 0
        
        # Confirm the sale
        total_sale = sell_price * quantity_to_sell
        original_cost = avg_purchase_price * quantity_to_sell
        profit_loss = total_sale - original_cost
        
        print(f"\nSale summary:")
        print(f"Quantity: {quantity_to_sell} x {product_name}")
        print(f"Average purchase price: ${avg_purchase_price:.2f}")
        print(f"Original cost: ${original_cost:.2f}")
        print(f"Sale amount: ${total_sale:.2f}")
        
        if profit_loss >= 0:
            print(f"Profit: ${profit_loss:.2f}")
        else:
            print(f"Loss: ${-profit_loss:.2f}")
        
        confirm = input(f"\nConfirm this sale? (y/n): ")
        if confirm.lower() != 'y':
            print("Sale cancelled.")
            return
        
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Process the sale by updating purchase records (FIFO - oldest first)
    purchases_df = pd.read_csv('my_purchases.csv')
    
    # Sort by dateReceived to implement FIFO
    if 'dateReceived' in purchases_df.columns:
        purchases_df['dateReceived'] = pd.to_datetime(purchases_df['dateReceived'])
        purchases_df = purchases_df.sort_values('dateReceived')
    
    # Find available items for this product
    product_purchases = purchases_df[purchases_df['product_id'] == product_id].copy()
    
    # Add default status and sell columns if they don't exist
    if 'status' not in purchases_df.columns:
        purchases_df['status'] = None
    if 'sell_price' not in purchases_df.columns:
        purchases_df['sell_price'] = None
    if 'sell_date' not in purchases_df.columns:
        purchases_df['sell_date'] = None
    
    remaining_to_sell = quantity_to_sell
    
    for idx, purchase in product_purchases.iterrows():
        if remaining_to_sell <= 0:
            break
            
        # Skip already sold items
        if purchase.get('status') == 'SOLD':
            continue
            
        purchase_qty = purchase['quantity']
        
        if remaining_to_sell >= purchase_qty:
            # Sell entire purchase
            purchases_df.at[idx, 'status'] = 'SOLD'
            purchases_df.at[idx, 'sell_price'] = sell_price
            purchases_df.at[idx, 'sell_date'] = sell_date
            remaining_to_sell -= purchase_qty
        else:
            # Split purchase - need to create new records
            # Keep original as unsold with reduced quantity
            purchases_df.at[idx, 'quantity'] = purchase_qty - remaining_to_sell
            
            # Create new record for sold portion
            sold_record = purchase.copy()
            sold_record['quantity'] = remaining_to_sell
            sold_record['status'] = 'SOLD'
            sold_record['sell_price'] = sell_price
            sold_record['sell_date'] = sell_date
            
            purchases_df = pd.concat([purchases_df, pd.DataFrame([sold_record])], ignore_index=True)
            remaining_to_sell = 0
    
    # Convert dateReceived back to string format
    if 'dateReceived' in purchases_df.columns:
        purchases_df['dateReceived'] = purchases_df['dateReceived'].dt.strftime('%Y-%m-%d')
    
    # Save the updated DataFrame
    purchases_df.to_csv('my_purchases.csv', index=False)
    
    print(f"\n{quantity_to_sell} x {product_name} has been marked as SOLD for ${total_sale:.2f}.")
    
    if profit_loss >= 0:
        print(f"Congratulations! You made a profit of ${profit_loss:.2f}")
    else:
        print(f"You had a loss of ${-profit_loss:.2f} on this sale.")

def main():
    """
    Main menu for purchase tracking
    """
    while True:
        print("\n===== POKEMON SEALED PRODUCT COLLECTION TRACKER =====")
        print("1. Add a new purchase")
        print("2. View your purchases")
        print("3. View inventory summary")
        print("4. Mark product as opened")
        print("5. Sell a product")
        print("6. Visualize collection value (run visualize_collection.py)")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        if choice == '1':
            add_purchase()
        elif choice == '2':
            view_purchases()
        elif choice == '3':
            view_inventory()
        elif choice == '4':
            open_product()
        elif choice == '5':
            sell_product()
        elif choice == '6':
            print("Please run visualize_collection.py to see your collection's value over time.")
        elif choice == '7':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
