from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncpg
from fastapi import HTTPException
import json

class ReservationService:
    def __init__(self, pool):
        self.pool = pool
        self.reservation_queues: Dict[int, List[dict]] = {}  # book_id -> list of queued reservations

    async def can_make_reservation(self, customer_id: int, book_id: int, days: int) -> bool:
        async with self.pool.acquire() as conn:
            # Check customer subscription status
            customer = await conn.fetchrow(
                "SELECT subscription_model, subscription_end_time FROM customers WHERE customer_id = $1",
                customer_id
            )
            
            if not customer:
                raise HTTPException(status_code=404, detail="Customer not found")

            if customer['subscription_model'] == 'free':
                raise HTTPException(status_code=403, detail="Free users cannot make reservations")

            max_days = 7 if customer['subscription_model'] == 'plus' else 14
            if days > max_days:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Maximum reservation time for you is {max_days} days"
                )

            # Check simultaneous reservations
            current_reservations = await conn.fetch(
                """
                SELECT COUNT(*) as count 
                FROM reservations 
                WHERE customer_id = $1 AND end_time > NOW()
                """,
                customer_id
            )
            max_simultaneous = 5 if customer['subscription_model'] == 'plus' else 10
            if current_reservations[0]['count'] >= max_simultaneous:
                raise HTTPException(
                    status_code=400,
                    detail=f"You cannot reserve more than {max_simultaneous} books simultaneously"
                )

            return True

    async def calculate_price(self, customer_id: int, days: int) -> float:
        base_price = 1000 * days  # 1000 tomans per day
        
        async with self.pool.acquire() as conn:
            # Check customer discounts
            customer = await conn.fetchrow(
                "SELECT subscription_model FROM customers WHERE customer_id = $1",
                customer_id
            )

            if customer['subscription_model'] == 'premium':
                base_price = 2000 * days  # 2000 tomans per day for Premium users
            
            if customer['subscription_model'] == 'plus':
                # Check number of books read in the last month
                month_books = await conn.fetchval(
                    """
                    SELECT COUNT(DISTINCT book_id) 
                    FROM reservations 
                    WHERE customer_id = $1 
                    AND end_time BETWEEN NOW() - INTERVAL '30 days' AND NOW()
                    """,
                    customer_id
                )
                
                if month_books >= 3:
                    base_price *= 0.7  # 30% discount
                
                # Check amount paid in the last two months
                total_paid = await conn.fetchval(
                    """
                    SELECT SUM(price) 
                    FROM reservations 
                    WHERE customer_id = $1 
                    AND start_time BETWEEN NOW() - INTERVAL '60 days' AND NOW()
                    """,
                    customer_id
                )
                
                if total_paid and total_paid >= 300000:
                    base_price = 0  # Free
            
            return base_price

    async def create_reservation(self, customer_id: int, book_id: int, days: int):
        if not await self.can_make_reservation(customer_id, book_id, days):
            raise HTTPException(status_code=403, detail="Reservation not possible")

        async with self.pool.acquire() as conn:
            # Check book availability
            book = await conn.fetchrow(
                "SELECT units FROM books WHERE book_id = $1",
                book_id
            )

            if not book:
                raise HTTPException(status_code=404, detail="Book not found")

            if book['units'] > 0:
                # Instant reservation
                price = await self.calculate_price(customer_id, days)
                
                # Check wallet balance
                wallet = await conn.fetchval(
                    "SELECT wallet FROM customers WHERE customer_id = $1",
                    customer_id
                )
                
                if wallet < price:
                    raise HTTPException(
                        status_code=400,
                        detail="Insufficient wallet balance"
                    )

                # Create reservation and deduct balance
                start_time = datetime.now()
                end_time = start_time + timedelta(days=days)
                
                async with conn.transaction():
                    reservation_id = await conn.fetchval(
                        """
                        INSERT INTO reservations (customer_id, book_id, start_time, end_time, price)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING reservation_id
                        """,
                        customer_id, book_id, start_time, end_time, price
                    )
                    
                    await conn.execute(
                        "UPDATE books SET units = units - 1 WHERE book_id = $1",
                        book_id
                    )
                    
                    await conn.execute(
                        "UPDATE customers SET wallet = wallet - $1 WHERE customer_id = $2",
                        price, customer_id
                    )

                return {
                    "reservation_id": reservation_id,
                    "book_id": book_id,
                    "customer_id": customer_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "price": price,
                    "status": "instant"
                }
            
            else:
                # Add to queue
                customer = await conn.fetchrow(
                    "SELECT subscription_model FROM customers WHERE customer_id = $1",
                    customer_id
                )
                
                queue_item = {
                    "customer_id": customer_id,
                    "days": days,
                    "request_time": datetime.now(),
                    "subscription_type": customer['subscription_model']
                }
                
                if book_id not in self.reservation_queues:
                    self.reservation_queues[book_id] = []
                
                self.reservation_queues[book_id].append(queue_item)
                self.reservation_queues[book_id].sort(
                    key=lambda x: (
                        0 if x['subscription_type'] == 'premium' else 1,
                        x['request_time']
                    )
                )
                
                position = self.reservation_queues[book_id].index(queue_item) + 1
                
                return {
                    "reservation_id": None,
                    "book_id": book_id,
                    "customer_id": customer_id,
                    "start_time": None,
                    "end_time": None,
                    "price": None,
                    "status": "queued",
                    "queue_position": position
                }