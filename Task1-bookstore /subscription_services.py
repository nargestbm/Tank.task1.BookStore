from fastapi import HTTPException
import asyncpg
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

class SubscriptionService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        
        # Subscription prices
        self.PLUS_PRICE = Decimal('50000')  # 50,000 tomans monthly
        self.PREMIUM_PRICE = Decimal('200000')  # 200,000 tomans monthly

    async def get_subscription_info(self, customer_id: int) -> dict:
        """Get customer subscription information"""
        async with self.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT subscription_model, subscription_end_time, wallet
                FROM customers 
                WHERE customer_id = $1
                """,
                customer_id
            )
            
            if not customer:
                raise HTTPException(status_code=404, detail="Customer not found")
                
            return dict(customer)

    async def upgrade_subscription(self, customer_id: int, new_model: str, months: int = 1) -> dict:
        """Upgrade or renew subscription"""
        if new_model not in ['plus', 'premium']:
            raise HTTPException(status_code=400, detail="Invalid subscription model")
            
        price = self.PLUS_PRICE if new_model == 'plus' else self.PREMIUM_PRICE
        total_price = price * months
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Check wallet balance
                customer = await conn.fetchrow(
                    "SELECT wallet, subscription_end_time FROM customers WHERE customer_id = $1",
                    customer_id
                )
                
                if not customer:
                    raise HTTPException(status_code=404, detail="Customer not found")
                    
                if customer['wallet'] < total_price:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Insufficient wallet balance. Current balance: {customer['wallet']} tomans"
                    )
                
                # Calculate new subscription end time
                current_time = datetime.now()
                if customer['subscription_end_time'] and customer['subscription_end_time'] > current_time:
                    # If active subscription exists, add to it
                    new_end_time = customer['subscription_end_time'] + timedelta(days=30 * months)
                else:
                    # New subscription starts now
                    new_end_time = current_time + timedelta(days=30 * months)
                
                # Update customer information
                updated_customer = await conn.fetchrow(
                    """
                    UPDATE customers 
                    SET subscription_model = $1,
                        subscription_end_time = $2,
                        wallet = wallet - $3
                    WHERE customer_id = $4
                    RETURNING *
                    """,
                    new_model, new_end_time, total_price, customer_id
                )
                
                return dict(updated_customer)

    async def add_wallet_balance(self, customer_id: int, amount: Decimal) -> dict:
        """Increase wallet balance"""
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")
            
        async with self.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                UPDATE customers 
                SET wallet = wallet + $1
                WHERE customer_id = $2
                RETURNING *
                """,
                amount, customer_id
            )
            
            if not customer:
                raise HTTPException(status_code=404, detail="Customer not found")
                
            return dict(customer)

    async def get_wallet_balance(self, customer_id: int) -> Decimal:
        """Get wallet balance"""
        async with self.pool.acquire() as conn:
            balance = await conn.fetchval(
                "SELECT wallet FROM customers WHERE customer_id = $1",
                customer_id
            )
            
            if balance is None:
                raise HTTPException(status_code=404, detail="Customer not found")
                
            return balance