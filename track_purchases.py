import pandas as pd
import os
from datetime import datetime
import re
from thefuzz import process, fuzz

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
            
        print(f"{idx+1}. {purchase['purchase_date']} - {purchase['quantity']} x {purchase['product_name']}{status}")
        print(f"   Price: ${purchase['purchase_price']:.2f} each, Total: ${purchase['total_cost']:.2f}")
    
    # Show overall stats
    # Check if status column exists before filtering
    if 'status' in purchases_df.columns:
        active_purchases = purchases_df[purchases_df['status'] != 'SOLD']
    else:
        # If no status column, assume all purchases are active
        active_purchases = purchases_df.copy()
    
    total_items = active_purchases['quantity'].sum()
    total_spent = active_purchases['total_cost'].sum()
    
    # Calculate revenue from sold items
    sold_revenue = 0
    if 'sell_price' in purchases_df.columns and 'sell_date' in purchases_df.columns:
        sold_items = purchases_df[purchases_df['status'] == 'SOLD']
        if not sold_items.empty:
            sold_revenue = (sold_items['quantity'] * sold_items['sell_price']).sum()
    
    print("\n===== COLLECTION SUMMARY =====")
    print(f"Active items in collection: {total_items}")
    print(f"Total spent on active items: ${total_spent:.2f}")
    if total_items > 0:
        print(f"Average cost per active item: ${total_spent / total_items:.2f}")
    
    if sold_revenue > 0:
        print(f"Total revenue from sold items: ${sold_revenue:.2f}")
        
    return purchases_df

def open_product():
    """
    Mark a product as opened in your collection
    """
    purchases_df = view_purchases()
    if purchases_df is None or purchases_df.empty:
        return
    
    # Select which product to open
    selection = input("\nEnter the number of the product you want to mark as opened (or 0 to cancel): ")
    try:
        selection_idx = int(selection) - 1
        if selection_idx < 0:
            print("Operation cancelled.")
            return
        
        selected_purchase = purchases_df.iloc[selection_idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return
    
    # Ensure the product isn't already sold
    if 'status' in selected_purchase and selected_purchase['status'] == 'SOLD':
        print("This product has already been sold and cannot be marked as opened.")
        return
    
    # Confirm
    product_name = selected_purchase['product_name']
    confirm = input(f"Are you sure you want to mark {product_name} as OPENED? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update the status to OPENED
    purchases_df.at[selection_idx, 'status'] = 'OPENED'
    
    # Save the updated DataFrame
    purchases_df.to_csv('my_purchases.csv', index=False)
    
    print(f"\n{product_name} has been marked as OPENED.")
    print("Note: This doesn't change the financial tracking of your collection.")

def sell_product():
    """
    Mark a product as sold in your collection and record the selling price
    """
    purchases_df = view_purchases()
    if purchases_df is None or purchases_df.empty:
        return
    
    # Select which product to sell
    selection = input("\nEnter the number of the product you sold (or 0 to cancel): ")
    try:
        selection_idx = int(selection) - 1
        if selection_idx < 0:
            print("Operation cancelled.")
            return
        
        selected_purchase = purchases_df.iloc[selection_idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return
    
    # Ensure the product isn't already sold
    if 'status' in selected_purchase and selected_purchase['status'] == 'SOLD':
        print("This product has already been sold.")
        return
    
    # Get selling details
    try:
        product_name = selected_purchase['product_name']
        quantity = selected_purchase['quantity']
        
        print(f"\nSelling {quantity} x {product_name}")
        
        sell_price = float(input("What price did you sell each item for? $"))
        if sell_price <= 0:
            print("Price must be greater than 0.")
            return
        
        date_input = input("When did you sell it? (YYYY-MM-DD, leave blank for today): ")
        if date_input:
            sell_date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            sell_date = datetime.now().strftime("%Y-%m-%d")
        
        # Confirm the sale
        total_sale = sell_price * quantity
        original_cost = selected_purchase['purchase_price'] * quantity
        profit_loss = total_sale - original_cost
        
        print(f"\nSale summary:")
        print(f"Original purchase: ${original_cost:.2f}")
        print(f"Sale amount: ${total_sale:.2f}")
        
        if profit_loss >= 0:
            print(f"Profit: ${profit_loss:.2f}")
        else:
            print(f"Loss: ${-profit_loss:.2f}")
        
        confirm = input(f"\nConfirm this sale? (y/n): ")
        if confirm.lower() != 'y':
            print("Sale cancelled.")
            return
        
        # Update the purchase record
        purchases_df.at[selection_idx, 'status'] = 'SOLD'
        purchases_df.at[selection_idx, 'sell_price'] = sell_price
        purchases_df.at[selection_idx, 'sell_date'] = sell_date
        
        # Save the updated DataFrame
        purchases_df.to_csv('my_purchases.csv', index=False)
        
        print(f"\n{product_name} has been marked as SOLD for ${total_sale:.2f}.")
        
    except ValueError as e:
        print(f"Error: {e}")
        return

def main():
    """
    Main menu for purchase tracking
    """
    while True:
        print("\n===== POKEMON SEALED PRODUCT COLLECTION TRACKER =====")
        print("1. Add a new purchase")
        print("2. View your purchases")
        print("3. Mark product as opened")
        print("4. Sell a product")
        print("5. Visualize collection value (run visualize_collection.py)")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == '1':
            add_purchase()
        elif choice == '2':
            view_purchases()
        elif choice == '3':
            open_product()
        elif choice == '4':
            sell_product()
        elif choice == '5':
            print("Please run visualize_collection.py to see your collection's value over time.")
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
