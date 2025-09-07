from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel
from transaction_manager import TransactionManager
import json
from thefuzz import fuzz, process
import numpy as np
from decimal import Decimal, ROUND_HALF_UP

def round_price(price):
    """Round price to 2 decimal places using proper decimal handling"""
    if price is None:
        return None
    return float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

app = FastAPI(title="Pokemon Sealed Tracker", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize transaction manager
tm = TransactionManager()

# Pydantic models
class TransactionCreate(BaseModel):
    product_id: str
    transaction_type: str
    quantity: int
    input_date: date
    price_per_unit: Optional[float] = None
    notes: Optional[str] = ""
    purchase_method: Optional[str] = None  # 'online' or 'in_person'
    purchase_location: Optional[str] = None
    
    def __init__(self, **data):
        if 'price_per_unit' in data and data['price_per_unit'] is not None:
            data['price_per_unit'] = round_price(data['price_per_unit'])
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

@app.get("/")
async def read_root():
    try:
        with open("templates/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content)
    except FileNotFoundError:
        return HTMLResponse("<h1>Welcome to Pokemon Tracker API</h1><p>Frontend template not found. Please ensure templates/index.html exists.</p>")

@app.get("/api/products/search")
async def search_products(q: str = Query(..., min_length=1), limit: int = 10):
    """Advanced fuzzy search with multiple algorithms for best results"""
    if not q:
        return {"products": []}
    
    products_df = tm.products_df
    query = q.lower().strip()
    
    # Create comprehensive search strings
    search_data = []
    for _, row in products_df.iterrows():
        # Combine multiple fields for better matching
        search_str = f"{row['name']} {row.get('cleanName', '')}".strip()
        search_data.append({
            'text': search_str,
            'product_id': row['productId'],
            'name': row['name'],
            'clean_name': row.get('cleanName', ''),
            'earliest_date': row['earliestDate'].isoformat()
        })
    
    # Normalize search texts for better matching
    search_texts = [item['text'] for item in search_data]
    
    # Strategy 1: Exact substring matches (highest priority)
    exact_matches = []
    for i, text in enumerate(search_texts):
        if query in text.lower():
            exact_matches.append((text, 100))
    
    # Strategy 2: Word-based matching (check if all query words exist)
    query_words = query.split()
    word_matches = []
    for i, text in enumerate(search_texts):
        text_lower = text.lower()
        matching_words = sum(1 for word in query_words if word in text_lower)
        if matching_words > 0:
            # Score based on percentage of query words found
            score = (matching_words / len(query_words)) * 90
            word_matches.append((text, score))
    
    # Strategy 3: Fuzzy matching with multiple algorithms
    partial_matches = process.extract(query, search_texts, limit=limit*3, scorer=fuzz.partial_ratio)
    token_matches = process.extract(query, search_texts, limit=limit*3, scorer=fuzz.token_sort_ratio)
    token_set_matches = process.extract(query, search_texts, limit=limit*3, scorer=fuzz.token_set_ratio)
    
    # Combine and score results
    scored_results = {}
    
    # Process exact matches first (highest weight)
    for match_text, score in exact_matches:
        for item in search_data:
            if item['text'] == match_text:
                product_id = item['product_id']
                scored_results[product_id] = {
                    'product': item,
                    'max_score': score,
                    'weighted_score': score * 1.2  # Boost exact matches
                }
                break
    
    # Process word matches
    for match_text, score in word_matches:
        if score > 20:  # Lower threshold for word matches
            for item in search_data:
                if item['text'] == match_text:
                    product_id = item['product_id']
                    if product_id not in scored_results:
                        scored_results[product_id] = {
                            'product': item,
                            'max_score': 0,
                            'weighted_score': 0
                        }
                    
                    weighted_score = score * 1.0
                    scored_results[product_id]['max_score'] = max(scored_results[product_id]['max_score'], score)
                    scored_results[product_id]['weighted_score'] = max(scored_results[product_id]['weighted_score'], weighted_score)
                    break
    
    # Process fuzzy matches
    for matches, weight in [(partial_matches, 0.9), (token_matches, 0.8), (token_set_matches, 0.7)]:
        for match_text, score in matches:
            if score > 25:  # Lower threshold for better recall
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
    
    # Sort by weighted score and return top results
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
            'score': result['max_score']
        })
    
    return {"products": products}

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get detailed product information"""
    try:
        product_info = tm.get_product_info(product_id)
        current_qty = tm.get_current_quantity(product_id)
        
        return {
            'productId': product_info['productId'],
            'name': product_info['name'],
            'cleanName': product_info.get('cleanName', ''),
            'earliestDate': product_info['earliestDate'].isoformat(),
            'currentQuantity': current_qty
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Product not found: {str(e)}")

@app.post("/api/transactions")
async def add_transaction(transaction: TransactionCreate):
    """Add a new transaction"""
    try:
        transaction_id = tm.add_transaction(
            product_id=transaction.product_id,
            transaction_type=transaction.transaction_type,
            quantity=transaction.quantity,
            input_date=transaction.input_date,
            price_per_unit=transaction.price_per_unit,
            notes=transaction.notes,
            purchase_method=transaction.purchase_method,
            purchase_location=transaction.purchase_location
        )
        
        # Check if date was adjusted
        adjusted_date, was_adjusted = tm.validate_transaction_date(
            transaction.product_id, 
            transaction.input_date
        )
        
        return {
            'transaction_id': transaction_id,
            'adjusted_date': adjusted_date.isoformat() if was_adjusted else None,
            'was_adjusted': was_adjusted,
            'message': 'Transaction added successfully'
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary statistics"""
    summary = tm.get_portfolio_summary()
    return summary

@app.get("/api/portfolio/chart-data")
async def get_portfolio_chart_data():
    """Get portfolio value chart data"""
    daily_values = tm.db.get_daily_portfolio_value()
    
    if daily_values.empty:
        return {"dates": [], "market_values": [], "cost_basis": []}
    
    # Convert to lists for JSON serialization
    daily_values['date'] = pd.to_datetime(daily_values['date'])
    
    return {
        "dates": daily_values['date'].dt.strftime('%Y-%m-%d').tolist(),
        "market_values": daily_values['total_market_value'].tolist(),
        "cost_basis": daily_values['total_cost_basis'].tolist()
    }

@app.get("/api/portfolio/holdings")
async def get_portfolio_holdings():
    """Get current portfolio holdings"""
    holdings = tm.db.get_portfolio_holdings()
    
    if holdings.empty:
        return {"holdings": []}
    
    # Get latest market prices
    latest_prices = tm.get_latest_market_prices()
    
    # Calculate current market values
    if not latest_prices.empty:
        price_lookup = latest_prices.set_index('productId')['marketPrice'].to_dict()
        # Round market prices
        price_lookup = {k: round_price(v) for k, v in price_lookup.items()}
        holdings['current_price_per_unit'] = holdings['product_id'].map(price_lookup).fillna(0)
        holdings['total_current_value'] = holdings['current_quantity'] * holdings['current_price_per_unit']
        # Round calculated values
        holdings['total_current_value'] = holdings['total_current_value'].apply(round_price)
    else:
        holdings['current_price_per_unit'] = 0
        holdings['total_current_value'] = 0
    
    # Convert to list of dictionaries
    holdings_list = []
    for _, row in holdings.iterrows():
        holdings_list.append({
            'product_name': row['product_name'],
            'current_quantity': int(row['current_quantity']),
            'average_cost_per_unit': round_price(float(row['average_cost_per_unit'])),
            'total_cost_basis': round_price(float(row['total_cost_basis'])),
            'current_price_per_unit': round_price(float(row['current_price_per_unit'])),
            'total_current_value': round_price(float(row['total_current_value']))
        })
    
    return {"holdings": holdings_list}

@app.get("/api/transactions")
async def get_transactions(transaction_type: Optional[str] = None):
    """Get transaction history"""
    if transaction_type and transaction_type != "All":
        transactions = tm.db.get_transactions(transaction_type=transaction_type)
    else:
        transactions = tm.db.get_transactions()
    
    if transactions.empty:
        return {"transactions": []}
    
    # Convert to list of dictionaries
    transactions_list = []
    for _, row in transactions.iterrows():
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
            'purchase_location': row.get('purchase_location', None)
        })
    
    return {"transactions": transactions_list}

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    """Delete a transaction"""
    try:
        # Get transaction details first
        transactions = tm.db.get_transactions()
        transaction = transactions[transactions['transaction_id'] == transaction_id]
        
        if transaction.empty:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        trans_row = transaction.iloc[0]
        
        # Mark as deleted
        conn = tm.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE transactions SET is_deleted = TRUE WHERE transaction_id = ?", 
                     (transaction_id,))
        conn.commit()
        conn.close()
        
        # Update portfolio holdings
        tm.db.update_portfolio_holdings(trans_row['product_id'], trans_row['product_name'])
        
        # Recalculate daily values
        tm.recalculate_daily_values_from_date(pd.to_datetime(trans_row['transaction_date']).date())
        
        return {"message": "Transaction deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting transaction: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Pokemon Tracker FastAPI Server...")
    print("📱 Open your browser to: http://localhost:8000")
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=False)
