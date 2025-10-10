"""
Transaction Editor
Provides inline editing capabilities for transactions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import date

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

class TransactionEdit(BaseModel):
    quantity: Optional[int] = None
    price_per_unit: Optional[float] = None
    notes: Optional[str] = None
    purchase_method: Optional[str] = None
    purchase_location: Optional[str] = None

@router.patch("/{transaction_id}")
async def partial_update_transaction(transaction_id: int, updates: TransactionEdit):
    """Partially update a transaction (PATCH operation)"""
    try:
        conn = sqlite3.connect("pokemon_transactions.db")
        cursor = conn.cursor()
        
        # Get existing transaction
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        if updates.quantity is not None:
            update_fields.append("quantity = ?")
            params.append(updates.quantity)
            
        if updates.price_per_unit is not None:
            update_fields.append("price_per_unit = ?")
            params.append(updates.price_per_unit)
            # Recalculate total_amount
            update_fields.append("total_amount = quantity * ?")
            params.append(updates.price_per_unit)
            
        if updates.notes is not None:
            update_fields.append("notes = ?")
            params.append(updates.notes)
            
        if updates.purchase_method is not None:
            update_fields.append("purchase_method = ?")
            params.append(updates.purchase_method)
            
        if updates.purchase_location is not None:
            update_fields.append("purchase_location = ?")
            params.append(updates.purchase_location)
        
        if not update_fields:
            conn.close()
            return {"message": "No fields to update"}
        
        # Execute update
        query = f"UPDATE transactions SET {', '.join(update_fields)} WHERE transaction_id = ?"
        params.append(transaction_id)
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        # Trigger portfolio recompilation
        from web_app import run_portfolio_recompiler
        run_portfolio_recompiler()
        
        return {"message": "Transaction updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating transaction: {str(e)}")
