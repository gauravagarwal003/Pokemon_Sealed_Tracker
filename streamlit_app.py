import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from transaction_manager import TransactionManager
from fuzzywuzzy import fuzz, process

# Page config
st.set_page_config(
    page_title="Pokemon Transaction Tracker",
    page_icon="🃏",
    layout="wide"
)

# Initialize session state
if 'transaction_manager' not in st.session_state:
    st.session_state.transaction_manager = TransactionManager()

def fuzzy_search_products(search_term, products_df, limit=10):
    """Fuzzy search for products"""
    if not search_term:
        return products_df.head(limit)
    
    # Create search strings combining name and clean name
    search_strings = []
    for _, row in products_df.iterrows():
        search_str = f"{row['name']} {row.get('cleanName', '')}"
        search_strings.append((search_str, row['productId'], row['name']))
    
    # Get fuzzy matches
    choices = [item[0] for item in search_strings]
    matches = process.extract(search_term, choices, limit=limit, scorer=fuzz.partial_ratio)
    
    # Filter by score threshold and return product IDs
    matched_ids = []
    for match in matches:
        if match[1] > 50:  # Minimum score threshold
            # Find the original product ID
            for search_str, product_id, product_name in search_strings:
                if search_str == match[0]:
                    matched_ids.append(product_id)
                    break
    
    return products_df[products_df['productId'].isin(matched_ids)]

def create_portfolio_chart(daily_values_df):
    """Create portfolio value chart"""
    if daily_values_df.empty:
        st.warning("No portfolio data available for charting.")
        return None
    
    # Convert date column to datetime
    daily_values_df['date'] = pd.to_datetime(daily_values_df['date'])
    
    # Create figure with single y-axis
    fig = go.Figure()
    
    # Collection Value line
    fig.add_trace(
        go.Scatter(
            x=daily_values_df['date'], 
            y=daily_values_df['total_market_value'],
            name="Collection Value",
            line=dict(color='blue', width=3),
            hovertemplate='<b>Collection Value</b><br>Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
        )
    )
    
    # Cost Basis line
    fig.add_trace(
        go.Scatter(
            x=daily_values_df['date'], 
            y=daily_values_df['total_cost_basis'],
            name="Cost Basis",
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='<b>Cost Basis</b><br>Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
        )
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': "Portfolio Performance Over Time",
            'x': 0.5,
            'xanchor': 'center'
        },
        height=600,
        hovermode='x unified',
        xaxis_title="Date",
        yaxis_title="Value ($)",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    
    # Format y-axis to show dollar signs
    fig.update_yaxes(tickformat='$,.0f')
    
    return fig

def main():
    st.title("🃏 Pokemon Collection Transaction Tracker")
    
    tm = st.session_state.transaction_manager
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Add Transaction", "Portfolio Overview", "Transaction History"])
    
    if page == "Add Transaction":
        st.header("Add New Transaction")
        
        # Transaction type selection
        transaction_type = st.selectbox("Transaction Type", ["BUY", "SELL", "OPEN"])
        
        # Product search with fuzzy matching
        st.subheader("Select Product")
        search_term = st.text_input("Search for product:", placeholder="Type product name...")
        
        if search_term:
            # Get fuzzy search results
            search_results = fuzzy_search_products(search_term, tm.products_df, limit=10)
            
            if not search_results.empty:
                # Create display options
                display_options = []
                product_map = {}
                
                for _, product in search_results.iterrows():
                    display_name = f"{product['name']} (ID: {product['productId']})"
                    display_options.append(display_name)
                    product_map[display_name] = product['productId']
                
                selected_display = st.selectbox("Select product:", display_options)
                selected_product_id = product_map[selected_display]
                
                # Show product details
                product_info = tm.get_product_info(selected_product_id)
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Product ID:** {product_info['productId']}")
                    st.write(f"**Name:** {product_info['name']}")
                with col2:
                    st.write(f"**Earliest Date:** {product_info['earliestDate'].strftime('%Y-%m-%d')}")
                    if transaction_type in ['SELL', 'OPEN']:
                        current_qty = tm.get_current_quantity(selected_product_id)
                        st.write(f"**Current Quantity:** {current_qty}")
                
                # Transaction details
                st.subheader("Transaction Details")
                
                col1, col2 = st.columns(2)
                with col1:
                    quantity = st.number_input("Quantity:", min_value=1, value=1)
                    
                with col2:
                    if transaction_type in ['BUY', 'SELL']:
                        # Use text input to allow decimal places like 29.03
                        price_input = st.text_input("Price per unit ($):", value="0.00", placeholder="e.g., 29.03")
                        try:
                            price_per_unit = float(price_input)
                            if price_per_unit <= 0:
                                st.error("Price must be greater than 0")
                                price_per_unit = None
                        except ValueError:
                            st.error("Invalid price format. Please enter a valid number (e.g., 29.03)")
                            price_per_unit = None
                    else:
                        price_per_unit = None
                        st.write("*No price required for OPEN transactions*")
                
                transaction_date = st.date_input("Transaction Date:", value=date.today())
                notes = st.text_area("Notes (optional):")
                
                # Submit button
                if st.button("Add Transaction", type="primary"):
                    try:
                        transaction_id = tm.add_transaction(
                            product_id=selected_product_id,
                            transaction_type=transaction_type,
                            quantity=quantity,
                            input_date=transaction_date,
                            price_per_unit=price_per_unit,
                            notes=notes
                        )
                        
                        st.success(f"Transaction added successfully! Transaction ID: {transaction_id}")
                        
                        # Show adjustment warning if date was adjusted
                        adjusted_date, was_adjusted = tm.validate_transaction_date(selected_product_id, transaction_date)
                        if was_adjusted:
                            st.warning(f"Transaction date was adjusted from {transaction_date} to {adjusted_date} (product's earliest available date)")
                        
                        # Clear the search term to reset the form
                        st.rerun()
                        
                    except ValueError as e:
                        st.error(f"Error: {str(e)}")
                    except Exception as e:
                        st.error(f"Unexpected error: {str(e)}")
            else:
                st.info("No products found matching your search.")
        else:
            st.info("Start typing to search for products...")
    
    elif page == "Portfolio Overview":
        st.header("Portfolio Overview")
        
        # Portfolio summary
        summary = tm.get_portfolio_summary()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Products", summary['total_products'])
        with col2:
            st.metric("Total Quantity", summary['total_quantity'])
        with col3:
            st.metric("Total Cost Basis", f"${summary['total_cost_basis']:,.2f}")
        
        # Portfolio chart
        st.subheader("Portfolio Value Over Time")
        daily_values = tm.db.get_daily_portfolio_value()
        
        if not daily_values.empty:
            chart = create_portfolio_chart(daily_values)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No historical data available. Add some transactions to see the chart.")
        
        # Current holdings
        st.subheader("Current Holdings")
        holdings = tm.db.get_portfolio_holdings()
        
        if not holdings.empty:
            # Get latest market prices
            latest_prices = tm.get_latest_market_prices()
            
            # Format the dataframe for display
            display_holdings = holdings.copy()
            
            # Calculate current market values
            if not latest_prices.empty:
                # Merge with latest prices
                price_lookup = latest_prices.set_index('productId')['marketPrice'].to_dict()
                display_holdings['current_price_per_unit'] = display_holdings['product_id'].map(price_lookup)
                display_holdings['current_price_per_unit'] = display_holdings['current_price_per_unit'].fillna(0)
                display_holdings['total_current_value'] = display_holdings['current_quantity'] * display_holdings['current_price_per_unit']
            else:
                display_holdings['current_price_per_unit'] = 0
                display_holdings['total_current_value'] = 0
            
            # Select and rename columns for display
            display_holdings = display_holdings[[
                'product_name', 'current_quantity', 'average_cost_per_unit', 
                'total_cost_basis', 'current_price_per_unit', 'total_current_value'
            ]]
            
            # Ensure all numeric columns are properly typed
            numeric_cols = ['current_quantity', 'average_cost_per_unit', 'total_cost_basis', 'current_price_per_unit', 'total_current_value']
            for col in numeric_cols:
                display_holdings[col] = pd.to_numeric(display_holdings[col], errors='coerce')
            
            display_holdings.columns = [
                'Product Name', 'Quantity', 'Avg Cost/Unit', 'Total Cost Basis', 
                'Current Price/Unit', 'Total Current Value'
            ]
            
            # Format the display for better readability while preserving sortability
            display_df = display_holdings.copy()
            currency_cols = ['Avg Cost/Unit', 'Total Cost Basis', 'Current Price/Unit', 'Total Current Value']
            
            # Create styled version with proper formatting
            st.dataframe(
                display_df,
                width='stretch',
                hide_index=True,
                column_config={
                    'Product Name': st.column_config.TextColumn('Product Name', width='medium'),
                    'Quantity': st.column_config.NumberColumn('Quantity', format='%d'),
                    'Avg Cost/Unit': st.column_config.NumberColumn('Avg Cost/Unit', format='$%.2f'),
                    'Total Cost Basis': st.column_config.NumberColumn('Total Cost Basis', format='$%.2f'),
                    'Current Price/Unit': st.column_config.NumberColumn('Current Price/Unit', format='$%.2f'),
                    'Total Current Value': st.column_config.NumberColumn('Total Current Value', format='$%.2f')
                }
            )
        else:
            st.info("No current holdings. Add some transactions to see your portfolio.")
    
    elif page == "Transaction History":
        st.header("Transaction History")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            filter_type = st.selectbox("Filter by type:", ["All", "BUY", "SELL", "OPEN"])
        with col2:
            # Product filter would go here - for now keeping it simple
            pass
        
        # Get transactions
        if filter_type == "All":
            transactions = tm.db.get_transactions()
        else:
            transactions = tm.db.get_transactions(transaction_type=filter_type)
        
        if not transactions.empty:
            st.subheader("Edit/Delete Transactions")
            st.warning("⚠️ Editing or deleting transactions will recalculate your portfolio values.")
            
            # Transaction selection for editing
            transaction_options = []
            transaction_map = {}
            
            for _, trans in transactions.iterrows():
                display_name = f"ID {trans['transaction_id']}: {trans['transaction_type']} {trans['quantity']}x {trans['product_name']} on {trans['transaction_date']}"
                if trans['price_per_unit'] is not None:
                    display_name += f" @ ${trans['price_per_unit']:.2f}"
                transaction_options.append(display_name)
                transaction_map[display_name] = trans['transaction_id']
            
            selected_transaction_display = st.selectbox("Select transaction to edit/delete:", 
                                                       [""] + transaction_options)
            
            if selected_transaction_display:
                selected_trans_id = transaction_map[selected_transaction_display]
                
                # Safety check: ensure the transaction still exists
                selected_trans_filter = transactions[transactions['transaction_id'] == selected_trans_id]
                if selected_trans_filter.empty:
                    st.error("Transaction not found. Please refresh the page.")
                    st.rerun()
                    return
                
                selected_trans = selected_trans_filter.iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🗑️ Delete Transaction", type="secondary"):
                        try:
                            # Mark as deleted
                            conn = tm.db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE transactions SET is_deleted = TRUE WHERE transaction_id = ?", 
                                         (selected_trans_id,))
                            conn.commit()
                            conn.close()
                            
                            # Update portfolio holdings
                            tm.db.update_portfolio_holdings(selected_trans['product_id'], selected_trans['product_name'])
                            
                            # Recalculate daily values
                            tm.recalculate_daily_values_from_date(pd.to_datetime(selected_trans['transaction_date']).date())
                            
                            st.success("Transaction deleted successfully!")
                            # Clear any editing session state
                            if 'editing_transaction' in st.session_state:
                                del st.session_state.editing_transaction
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error deleting transaction: {e}")
                
                with col2:
                    if st.button("✏️ Edit Transaction", type="primary"):
                        st.session_state.editing_transaction = selected_trans_id
                        st.rerun()
            
            # Edit form
            if 'editing_transaction' in st.session_state:
                st.subheader("Edit Transaction")
                edit_trans_id = st.session_state.editing_transaction
                
                # Safety check: ensure the transaction still exists
                edit_trans_filter = transactions[transactions['transaction_id'] == edit_trans_id]
                if edit_trans_filter.empty:
                    st.error("Transaction not found. It may have been deleted.")
                    del st.session_state.editing_transaction
                    st.rerun()
                    return
                
                edit_trans = edit_trans_filter.iloc[0]
                
                # Get product info
                product_info = tm.get_product_info(edit_trans['product_id'])
                
                st.write(f"**Editing:** {edit_trans['product_name']}")
                
                # Edit form
                edit_col1, edit_col2 = st.columns(2)
                
                with edit_col1:
                    new_quantity = st.number_input("Quantity:", min_value=1, value=int(edit_trans['quantity']))
                    
                with edit_col2:
                    if edit_trans['transaction_type'] in ['BUY', 'SELL']:
                        # Use text input to allow decimal places like 29.03
                        current_price = edit_trans['price_per_unit'] if edit_trans['price_per_unit'] is not None else 0.00
                        price_input = st.text_input("Price per unit ($):", value=f"{current_price:.2f}")
                        try:
                            new_price = float(price_input)
                        except ValueError:
                            new_price = current_price
                            st.error("Invalid price format. Please enter a valid number.")
                    else:
                        new_price = None
                        st.write("*No price required for OPEN transactions*")
                
                new_date = st.date_input("Transaction Date:", 
                                       value=pd.to_datetime(edit_trans['transaction_date']).date())
                new_notes = st.text_area("Notes:", value=edit_trans['notes'] or "")
                
                edit_button_col1, edit_button_col2 = st.columns(2)
                
                with edit_button_col1:
                    if st.button("💾 Save Changes", type="primary"):
                        try:
                            # Validate date
                            validated_date, was_adjusted = tm.validate_transaction_date(edit_trans['product_id'], new_date)
                            
                            # Calculate new total
                            new_total = new_quantity * new_price if new_price is not None else None
                            
                            # Update transaction
                            conn = tm.db.get_connection()
                            cursor = conn.cursor()
                            
                            cursor.execute('''
                                UPDATE transactions 
                                SET quantity = ?, price_per_unit = ?, total_amount = ?, 
                                    transaction_date = ?, input_date = ?, date_adjusted = ?, notes = ?
                                WHERE transaction_id = ?
                            ''', (new_quantity, new_price, new_total, 
                                  validated_date.strftime('%Y-%m-%d'), new_date.strftime('%Y-%m-%d'), 
                                  was_adjusted, new_notes, edit_trans_id))
                            
                            conn.commit()
                            conn.close()
                            
                            # Update portfolio holdings
                            tm.db.update_portfolio_holdings(edit_trans['product_id'], edit_trans['product_name'])
                            
                            # Recalculate daily values
                            tm.recalculate_daily_values_from_date(validated_date)
                            
                            if was_adjusted:
                                st.warning(f"Date adjusted from {new_date} to {validated_date} (product's earliest date)")
                            
                            st.success("Transaction updated successfully!")
                            del st.session_state.editing_transaction
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error updating transaction: {e}")
                
                with edit_button_col2:
                    if st.button("❌ Cancel", type="secondary"):
                        del st.session_state.editing_transaction
                        st.rerun()
            
            # Display transactions table
            st.subheader("All Transactions")
            # Format for display
            display_transactions = transactions.copy()
            display_transactions = display_transactions[[
                'transaction_id', 'transaction_date', 'product_name', 'transaction_type', 
                'quantity', 'price_per_unit', 'total_amount', 'notes'
            ]]
            display_transactions.columns = [
                'ID', 'Date', 'Product', 'Type', 'Quantity', 'Price/Unit', 'Total', 'Notes'
            ]
            
            # Format currency columns
            display_transactions['Price/Unit'] = display_transactions['Price/Unit'].apply(
                lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
            )
            display_transactions['Total'] = display_transactions['Total'].apply(
                lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
            )
            
            st.dataframe(display_transactions, use_container_width=True)
        else:
            st.info("No transactions found.")

if __name__ == "__main__":
    main()
