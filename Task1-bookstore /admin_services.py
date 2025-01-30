from fastapi import HTTPException
import asyncpg
from typing import List, Optional
from datetime import datetime

class AdminService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def revoke_user_token(self, admin_username: str, target_username: str) -> bool:
        """Revoke a user's token by admin"""
        async with self.pool.acquire() as conn:
            # Check admin access
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                admin_username
            )
            
            if not admin or admin['role'] != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="You don't have the required permissions for this operation"
                )
            
            # Check if target user exists
            target = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                target_username
            )
            
            if not target:
                raise HTTPException(
                    status_code=404,
                    detail="Target user not found"
                )
                
            if target['role'] == 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="Cannot revoke admin tokens"
                )
            
            # Revoke token by recording in revoked_tokens table
            await conn.execute(
                """
                INSERT INTO revoked_tokens (username, revoked_at, revoked_by)
                VALUES ($1, $2, $3)
                """,
                target_username, datetime.now(), admin_username
            )
            
            return True
    
    async def end_reservation(self, admin_username: str, reservation_id: int) -> bool:
        """End a reservation before its scheduled time"""
        async with self.pool.acquire() as conn:
            # Check admin access
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                admin_username
            )
            
            if not admin or admin['role'] != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="You don't have the required permissions for this operation"
                )
            
            # Check if reservation exists
            reservation = await conn.fetchrow(
                """
                SELECT r.*, b.units 
                FROM reservations r
                JOIN books b ON r.book_id = b.book_id
                WHERE r.reservation_id = $1
                """,
                reservation_id
            )
            
            if not reservation:
                raise HTTPException(
                    status_code=404,
                    detail="Reservation not found"
                )
            
            if reservation['end_time'] <= datetime.now():
                raise HTTPException(
                    status_code=400,
                    detail="This reservation has already ended"
                )
            
            async with conn.transaction():
                # End the reservation
                await conn.execute(
                    """
                    UPDATE reservations 
                    SET end_time = NOW(),
                        status = 'terminated_by_admin'
                    WHERE reservation_id = $1
                    """,
                    reservation_id
                )
                
                # Increase book inventory
                await conn.execute(
                    """
                    UPDATE books
                    SET units = units + 1
                    WHERE book_id = $1
                    """,
                    reservation['book_id']
                )
            
            return True
    
    async def get_book_status(self, admin_username: str, book_id: int) -> dict:
        """Get book status including current reservations and waiting queue"""
        async with self.pool.acquire() as conn:
            # Check admin access
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                admin_username
            )
            
            if not admin or admin['role'] != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="You don't have the required permissions for this operation"
                )
            
            # Get book information
            book = await conn.fetchrow(
                "SELECT * FROM books WHERE book_id = $1",
                book_id
            )
            
            if not book:
                raise HTTPException(
                    status_code=404,
                    detail="Book not found"
                )
            
            # Get active reservations
            active_reservations = await conn.fetch(
                """
                SELECT r.*, u.username, u.email 
                FROM reservations r
                JOIN customers c ON r.customer_id = c.customer_id
                JOIN users u ON c.user_id = u.user_id
                WHERE r.book_id = $1 AND r.end_time > NOW()
                ORDER BY r.start_time
                """,
                book_id
            )
            
            # Get waiting list
            waiting_list = await conn.fetch(
                """
                SELECT q.*, u.username, u.email, c.subscription_model
                FROM reservation_queue q
                JOIN customers c ON q.customer_id = c.customer_id
                JOIN users u ON c.user_id = u.user_id
                WHERE q.book_id = $1
                ORDER BY 
                    CASE WHEN c.subscription_model = 'premium' THEN 0 ELSE 1 END,
                    q.request_time
                """,
                book_id
            )
            
            return {
                "book": dict(book),
                "active_reservations": [dict(r) for r in active_reservations],
                "waiting_list": [dict(w) for w in waiting_list]
            }