"""
Enhanced Pokemon Sealed Tracker Web App
FastAPI application with full CRUD operations for transactions
Includes inline editing and automatic portfolio recompilation
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel
import json
from thefuzz import fuzz, process
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
import sqlite3
import subprocess
import sys
import glob

def round_price(price):
    """Round price to 2 decimal places using proper decimal handling"""
    if price is None:
        return None
    return float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

app = FastAPI(title="Pokemon Sealed Tracker", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DB_PATH = "pokemon_transactions.db"

# Load products data
try:
    products_df = pd.read_csv("sealed_products_tracking.csv")
    products_df['earliestDate'] = pd.to_datetime(products_df['earliestDate'])
    print(f"Loaded {len(products_df)} products from sealed_products_tracking.csv")
except FileNotFoundError:
    print("ERROR: sealed_products_tracking.csv not found")
    products_df = pd.DataFrame()

# Pydantic models
class TransactionCreate(BaseModel):
    product_id: str
    transaction_type: str
    quantity: int
    input_date: date
    price_per_unit: Optional[float] = None
    notes: Optional[str] = ""
    purchase_method: Optional[str] = None
    purchase_location: Optional[str] = None
    
    def __init__(self, **data):
        if 'price_per_unit' in data and data['price_per_unit'] is not None:
            data['price_per_unit'] = round_price(data['price_per_unit'])
        # Coerce product_id to string if numeric is passed
        if 'product_id' in data and data['product_id'] is not None:
            data['product_id'] = str(data['product_id'])
        super().__init__(**data)

class TransactionUpdate(BaseModel):
    quantity: int
    price_per_unit: Optional[float] = None
    input_date: date
    notes: Optional[str] = ""
    purchase_method: Optional[str] = None
    purchase_location: Optional[str] = None
    
    def __init__(self, **data):
        if 'price_per_unit' in data and data['price_per_unit'] is not None:
            data['price_per_unit'] = round_price(data['price_per_unit'])
        super().__init__(**data)

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

def run_portfolio_recompiler():
    """Run the portfolio recompiler after transaction changes"""
    try:
        print("Running portfolio recompiler...")
        result = subprocess.run([sys.executable, 'portfolio_recompiler.py'], 
                               capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("Portfolio recompiler completed successfully")
            return True
        else:
            print(f"Portfolio recompiler failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error running portfolio recompiler: {e}")
        return False

def validate_transaction_date(product_id, input_date):
    """Validate and adjust transaction date against product's earliest date"""
    if products_df.empty:
        return input_date, False
        
    # Ensure product_id is a string, convert to int for comparison
    product = products_df[products_df['productId'] == int(str(product_id))]
    if product.empty:
        raise ValueError(f"Product ID {product_id} not found")
    
    earliest_date = product.iloc[0]['earliestDate']
    input_date = pd.to_datetime(input_date)
    
    if input_date < earliest_date:
        return earliest_date.date(), True
    return input_date.date(), False

def validate_inventory_for_transaction(product_id, quantity, transaction_type, exclude_transaction_id=None):
    """Validate that sufficient inventory exists for SELL/OPEN transactions"""
    if transaction_type == 'BUY':
        return True
    
    conn = get_db_connection()
    query = """
        SELECT 
            COALESCE(SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN transaction_type = 'SELL' THEN quantity ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN transaction_type = 'OPEN' THEN quantity ELSE 0 END), 0) as current_quantity
        FROM transactions 
        WHERE product_id = ?
    """
    params = [product_id]
    
    if exclude_transaction_id:
        query += " AND transaction_id != ?"
        params.append(exclude_transaction_id)
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    
    current_quantity = result[0] if result and result[0] else 0
    return current_quantity >= quantity

@app.get("/")
async def read_root():
    try:
        with open("templates/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content)
    except FileNotFoundError:
        return HTMLResponse("<h1>Pokemon Tracker API</h1><p>Frontend template not found. Please ensure templates/index.html exists.</p>")

@app.get("/api/products/search")
async def search_products(q: str = Query(..., min_length=1), limit: int = 10):
    """Advanced fuzzy search with multiple algorithms for best results"""
    if not q or products_df.empty:
        return {"products": []}
    
    query = q.lower().strip()
    
    # Create comprehensive search strings
    search_data = []
    for _, row in products_df.iterrows():
        search_str = f"{row['name']} {row.get('cleanName', '')}".strip()
        search_data.append({
            'text': search_str,
            'product_id': row['productId'],
            'name': row['name'],
            'clean_name': row.get('cleanName', ''),
            'earliest_date': row['earliestDate'].isoformat()
        })
    
    search_texts = [item['text'] for item in search_data]
    
    # Multiple search strategies
    exact_matches = [(text, 100) for i, text in enumerate(search_texts) if query in text.lower()]
    
    query_words = query.split()
    word_matches = []
    for text in search_texts:
        text_lower = text.lower()
        matching_words = sum(1 for word in query_words if word in text_lower)
        if matching_words > 0:
            score = (matching_words / len(query_words)) * 90
            word_matches.append((text, score))
    
    # Fuzzy matching
    partial_matches = process.extract(query, search_texts, limit=limit*3, scorer=fuzz.partial_ratio)
    token_matches = process.extract(query, search_texts, limit=limit*3, scorer=fuzz.token_sort_ratio)
    token_set_matches = process.extract(query, search_texts, limit=limit*3, scorer=fuzz.token_set_ratio)
    
    # Combine and score results
    scored_results = {}
    
    for matches, weight in [(exact_matches, 1.2), (word_matches, 1.0), 
                           (partial_matches, 0.9), (token_matches, 0.8), (token_set_matches, 0.7)]:
        for match_text, score in matches:
            if score > 25:
                for item in search_data:
                    if item['text'] == match_text:
                        product_id = item['product_id']
                        if product_id not in scored_results:
                            scored_results[product_id] = {
                                'product': item,
                                'max_score': 0,
                                'weighted_score': 0
                            }
                        
                        weighted_score = score * weight
                        scored_results[product_id]['max_score'] = max(scored_results[product_id]['max_score'], score)
                        scored_results[product_id]['weighted_score'] = max(scored_results[product_id]['weighted_score'], weighted_score)
                        break
    
    # Sort and return top results
    sorted_results = sorted(
        scored_results.values(), 
        key=lambda x: (x['weighted_score'], x['max_score']), 
        reverse=True
    )[:limit]
    
    products = []
    for result in sorted_results:
        product = result['product']
        products.append({
            'productId': product['product_id'],
            'name': product['name'],
            'cleanName': product['clean_name'],
            'earliestDate': product['earliest_date'],
            'score': int(result['max_score'])
        })
    
    return {"products": products}

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get detailed product information"""
    try:
        if products_df.empty:
            raise HTTPException(status_code=404, detail="Products data not available")
        # Ensure product_id is a string, convert to int for comparison
        product = products_df[products_df['productId'] == int(str(product_id))]
        if product.empty:
            raise HTTPException(status_code=404, detail="Product not found")
        product_info = product.iloc[0]
        # Get current quantity from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN transaction_type = 'SELL' THEN quantity ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN transaction_type = 'OPEN' THEN quantity ELSE 0 END), 0) as current_quantity
            FROM transactions 
            WHERE product_id = ?
        """, (product_id,))
        result = cursor.fetchone()
        conn.close()
        current_quantity = result[0] if result and result[0] else 0
        return {
            'productId': product_info['productId'],
            'name': product_info['name'],
            'cleanName': product_info.get('cleanName', ''),
            'earliestDate': product_info['earliestDate'].isoformat(),
            'currentQuantity': current_quantity
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Product not found: {str(e)}")

@app.post("/api/transactions")
async def add_transaction(transaction: TransactionCreate):
    """Add a new transaction"""
    try:
        # Validate product exists
        if products_df.empty or products_df[products_df['productId'] == int(transaction.product_id)].empty:
            raise ValueError(f"Product ID {transaction.product_id} not found")
        
        product_info = products_df[products_df['productId'] == int(transaction.product_id)].iloc[0]
        product_name = product_info['name']
        
        # Validate and adjust date
        transaction_date, date_adjusted = validate_transaction_date(transaction.product_id, transaction.input_date)
        
        # Validate inventory for SELL/OPEN
        if transaction.transaction_type in ['SELL', 'OPEN']:
            if not validate_inventory_for_transaction(transaction.product_id, transaction.quantity, transaction.transaction_type):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'SELL' THEN quantity ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'OPEN' THEN quantity ELSE 0 END), 0) as current_quantity
                    FROM transactions 
                    WHERE product_id = ? AND is_deleted = FALSE
                """, (transaction.product_id,))
                result = cursor.fetchone()
                conn.close()
                current_qty = result[0] if result and result[0] else 0
                raise ValueError(f"Insufficient inventory. Current quantity: {current_qty}, Requested: {transaction.quantity}")
        
        # Validate price for BUY/SELL
        if transaction.transaction_type in ['BUY', 'SELL'] and transaction.price_per_unit is None:
            raise ValueError(f"Price per unit is required for {transaction.transaction_type} transactions")
        
        # Force None price for OPEN transactions
        if transaction.transaction_type == 'OPEN':
            transaction.price_per_unit = None
        
        # Validate purchase fields for BUY transactions
        if transaction.transaction_type == 'BUY':
            if not transaction.purchase_method:
                raise ValueError("Purchase method is required for BUY transactions")
            if not transaction.purchase_location or transaction.purchase_location.strip() == "":
                raise ValueError("Purchase location is required for BUY transactions")
        
        # Calculate total amount
        total_amount = None
        if transaction.price_per_unit is not None:
            total_amount = round_price(transaction.quantity * transaction.price_per_unit)
        
        # For non-BUY transactions, clear purchase fields so DB CHECK constraint isn't violated
        if transaction.transaction_type != 'BUY':
            transaction.purchase_method = None
            transaction.purchase_location = None

        # Add transaction to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions 
            (product_id, product_name, transaction_type, quantity, price_per_unit, 
             total_amount, transaction_date, input_date, date_adjusted, notes,
             purchase_method, purchase_location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(transaction.product_id), product_name, transaction.transaction_type,
            transaction.quantity, transaction.price_per_unit, total_amount,
            transaction_date.strftime('%Y-%m-%d'), transaction.input_date.strftime('%Y-%m-%d'),
            date_adjusted, transaction.notes, transaction.purchase_method, transaction.purchase_location
        ))
        
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Run portfolio recompiler
        recompiler_success = run_portfolio_recompiler()
        if not recompiler_success:
            print("Warning: Portfolio recompiler failed, but transaction was saved")
        
        return {
            'transaction_id': transaction_id,
            'adjusted_date': transaction_date.isoformat() if date_adjusted else None,
            'was_adjusted': date_adjusted,
            'message': 'Transaction added successfully'
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.put("/api/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, transaction: TransactionUpdate):
    """Update an existing transaction"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get existing transaction
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Get column names
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [row[1] for row in cursor.fetchall()]
        existing_dict = dict(zip(columns, existing))
        
        product_id = existing_dict['product_id']
        transaction_type = existing_dict['transaction_type']
        
        # Validate and adjust date
        transaction_date, date_adjusted = validate_transaction_date(product_id, transaction.input_date)
        
        # Validate inventory for SELL/OPEN (excluding this transaction)
        if transaction_type in ['SELL', 'OPEN']:
            if not validate_inventory_for_transaction(product_id, transaction.quantity, transaction_type, transaction_id):
                # Get current quantity for error message
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'SELL' THEN quantity ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'OPEN' THEN quantity ELSE 0 END), 0) as current_quantity
                    FROM transactions 
                    WHERE product_id = ? AND is_deleted = FALSE AND transaction_id != ?
                """, (product_id, transaction_id))
                result = cursor.fetchone()
                current_qty = result[0] if result and result[0] else 0
                conn.close()
                raise ValueError(f"Insufficient inventory. Available quantity (excluding this transaction): {current_qty}, Requested: {transaction.quantity}")
        
        # Validate price for BUY/SELL
        if transaction_type in ['BUY', 'SELL'] and transaction.price_per_unit is None:
            conn.close()
            raise ValueError(f"Price per unit is required for {transaction_type} transactions")
        
        # Force None price for OPEN transactions
        if transaction_type == 'OPEN':
            transaction.price_per_unit = None
        
        # Validate purchase fields for BUY transactions
        if transaction_type == 'BUY':
            if not transaction.purchase_method:
                conn.close()
                raise ValueError("Purchase method is required for BUY transactions")
            if not transaction.purchase_location or transaction.purchase_location.strip() == "":
                conn.close()
                raise ValueError("Purchase location is required for BUY transactions")
        
        # Calculate total amount
        total_amount = None
        if transaction.price_per_unit is not None:
            total_amount = round_price(transaction.quantity * transaction.price_per_unit)
        # For non-BUY transactions, clear purchase fields so DB CHECK constraint isn't violated
        if transaction.transaction_type != 'BUY':
            transaction.purchase_method = None
            transaction.purchase_location = None

        # Update transaction
        cursor.execute('''
            UPDATE transactions SET
                quantity = ?, price_per_unit = ?, total_amount = ?,
                transaction_date = ?, input_date = ?, date_adjusted = ?,
                notes = ?, purchase_method = ?, purchase_location = ?
            WHERE transaction_id = ?
        ''', (
            transaction.quantity, transaction.price_per_unit, total_amount,
            transaction_date.strftime('%Y-%m-%d'), transaction.input_date.strftime('%Y-%m-%d'),
            date_adjusted, transaction.notes, transaction.purchase_method,
            transaction.purchase_location, transaction_id
        ))
        
        conn.commit()
        conn.close()
        
        # Run portfolio recompiler
        recompiler_success = run_portfolio_recompiler()
        if not recompiler_success:
            print("Warning: Portfolio recompiler failed, but transaction was updated")
        
        return {
            'transaction_id': transaction_id,
            'adjusted_date': transaction_date.isoformat() if date_adjusted else None,
            'was_adjusted': date_adjusted,
            'message': 'Transaction updated successfully'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    """Delete a transaction (hard delete)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if transaction exists
        cursor.execute("SELECT transaction_id FROM transactions WHERE transaction_id = ?", 
                     (transaction_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Hard delete the transaction
        cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", 
                     (transaction_id,))
        conn.commit()
        conn.close()
        
        # Run portfolio recompiler
        recompiler_success = run_portfolio_recompiler()
        if not recompiler_success:
            print("Warning: Portfolio recompiler failed, but transaction was deleted")
        
        return {"message": "Transaction deleted successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error deleting transaction: {str(e)}")

def get_all_transactions(self):
    """Get all transactions (no soft delete filter needed)"""
    conn = self.get_connection()
    query = """
        SELECT * FROM transactions 
        ORDER BY transaction_date, created_at
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary statistics"""
    conn = get_db_connection()
    
    # Get holdings summary
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total_products,
            SUM(current_quantity) as total_quantity,
            SUM(total_cost_basis) as total_cost_basis
        FROM portfolio_holdings 
        WHERE current_quantity > 0
    """)
    holdings_result = cursor.fetchone()
    
    # Get latest market value
    cursor.execute("""
        SELECT total_cost_basis, total_market_value, unrealized_pnl, 
               COALESCE(cumulative_realized_pnl, 0) as cumulative_realized_pnl
        FROM daily_portfolio_value 
        ORDER BY date DESC 
        LIMIT 1
    """)
    latest_value_result = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_products': holdings_result[0] or 0,
        'total_quantity': holdings_result[1] or 0,
        # Use the daily_portfolio_value latest total_cost_basis so the UI number
        # matches the graph (which is drawn from daily_portfolio_value rows).
        'total_cost_basis': float(latest_value_result[0] if latest_value_result and latest_value_result[0] is not None else (holdings_result[2] or 0)),
        'current_market_value': float(latest_value_result[1] if latest_value_result and latest_value_result[1] is not None else 0),
        'unrealized_pnl': float(latest_value_result[2] if latest_value_result and latest_value_result[2] is not None else 0),
        'cumulative_realized_pnl': float(latest_value_result[3] if latest_value_result and latest_value_result[3] is not None else 0)
    }

@app.get("/api/portfolio/chart-data")
async def get_portfolio_chart_data():
    """Get portfolio value chart data"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM daily_portfolio_value ORDER BY date", conn)
    conn.close()
    
    if df.empty:
        return {"dates": [], "market_values": [], "cost_basis": []}
    
    df['date'] = pd.to_datetime(df['date'])
    
    return {
        "dates": df['date'].dt.strftime('%Y-%m-%d').tolist(),
        "market_values": df['total_market_value'].fillna(0).tolist(),
        "cost_basis": df['total_cost_basis'].fillna(0).tolist()
    }

@app.get("/api/portfolio/holdings")
async def get_portfolio_holdings():
    """Get current portfolio holdings with market values"""
    conn = get_db_connection()
    
    # Get holdings
    holdings_df = pd.read_sql_query("""
        SELECT * FROM portfolio_holdings 
        WHERE current_quantity > 0 
        ORDER BY product_name
    """, conn)
    
    if holdings_df.empty:
        conn.close()
        return {"holdings": []}
    
    # Get latest market prices
    try:
        price_files = glob.glob("daily_prices/market_prices_*.parquet")
        if price_files:
            latest_file = sorted(price_files)[-1]
            latest_prices = pd.read_parquet(latest_file)
            price_lookup = latest_prices.set_index('productId')['marketPrice'].to_dict()
            price_lookup = {k: round_price(v) for k, v in price_lookup.items() if pd.notna(v)}
        else:
            price_lookup = {}
    except:
        price_lookup = {}
    
    conn.close()
    
    # Calculate current market values
    holdings_list = []
    for _, row in holdings_df.iterrows():
        current_price = price_lookup.get(row['product_id'], 0.0)
        total_current_value = row['current_quantity'] * current_price
        
        holdings_list.append({
            'product_name': row['product_name'],
            'current_quantity': int(row['current_quantity']),
            'average_cost_per_unit': round_price(float(row['average_cost_per_unit'])),
            'total_cost_basis': round_price(float(row['total_cost_basis'])),
            'current_price_per_unit': round_price(current_price),
            'total_current_value': round_price(total_current_value)
        })
    
    return {"holdings": holdings_list}

@app.get("/api/transactions")
async def get_transactions(transaction_type: Optional[str] = None):
    """Get transaction history"""
    conn = get_db_connection()
    
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    
    if transaction_type and transaction_type != "All":
        query += " AND transaction_type = ?"
        params.append(transaction_type)
    
    query += " ORDER BY transaction_date DESC, created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df.empty:
        return {"transactions": []}
    
    # Convert to list of dictionaries
    transactions_list = []
    for _, row in df.iterrows():
        transactions_list.append({
            'transaction_id': int(row['transaction_id']),
            'transaction_date': row['transaction_date'],
            'product_name': row['product_name'],
            'transaction_type': row['transaction_type'],
            'quantity': int(row['quantity']),
            'price_per_unit': round_price(float(row['price_per_unit'])) if pd.notna(row['price_per_unit']) else None,
            'total_amount': round_price(float(row['total_amount'])) if pd.notna(row['total_amount']) else None,
            'notes': row['notes'] or "",
            'purchase_method': row.get('purchase_method', None),
            'purchase_location': row.get('purchase_location', None),
            'date_adjusted': bool(row.get('date_adjusted', False))
        })
    
    return {"transactions": transactions_list}

@app.post("/api/portfolio/update-prices")
async def update_prices_and_portfolio():
    """Manually trigger price update and portfolio recompilation"""
    try:
        print("Manual price update requested...")
        
        # Run the daily price tracker to get latest prices
        result = subprocess.run(
            [sys.executable, 'daily_price_tracker.py', '--force'], 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print("Price update completed successfully")
            print(result.stdout)
            return {
                'message': 'Prices updated successfully! Portfolio has been recompiled with latest market data.',
                'timestamp': datetime.now().isoformat(),
                'details': result.stdout
            }
        else:
            print(f"Price update failed: {result.stderr}")
            # Try to run just the portfolio recompiler in case prices are already current
            recompiler_success = run_portfolio_recompiler()
            if recompiler_success:
                return {
                    'message': 'Portfolio recompiled with existing price data. Price update may have failed - check logs.',
                    'timestamp': datetime.now().isoformat(),
                    'warning': result.stderr
                }
            else:
                raise HTTPException(status_code=500, detail=f"Price update failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Price update timed out after 5 minutes")
    except Exception as e:
        print(f"Error during manual price update: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating prices: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Pokemon Tracker FastAPI Server...")
    print("📱 Open your browser to: http://localhost:8000")
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=False)