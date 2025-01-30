from fastapi import HTTPException
import asyncpg
from typing import List, Optional
from datetime import datetime

class AdminService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def revoke_user_token(self, admin_username: str, target_username: str) -> bool:
        """لغو توکن یک کاربر توسط ادمین"""
        async with self.pool.acquire() as conn:
            # بررسی دسترسی ادمین
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                admin_username
            )
            
            if not admin or admin['role'] != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="شما دسترسی لازم برای این عملیات را ندارید"
                )
            
            # بررسی وجود کاربر هدف
            target = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                target_username
            )
            
            if not target:
                raise HTTPException(
                    status_code=404,
                    detail="کاربر مورد نظر یافت نشد"
                )
                
            if target['role'] == 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="امکان لغو توکن ادمین‌ها وجود ندارد"
                )
            
            # لغو توکن با ثبت در جدول revoked_tokens
            await conn.execute(
                """
                INSERT INTO revoked_tokens (username, revoked_at, revoked_by)
                VALUES ($1, $2, $3)
                """,
                target_username, datetime.now(), admin_username
            )
            
            return True
    
    async def end_reservation(self, admin_username: str, reservation_id: int) -> bool:
        """پایان دادن به یک رزرو قبل از موعد"""
        async with self.pool.acquire() as conn:
            # بررسی دسترسی ادمین
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                admin_username
            )
            
            if not admin or admin['role'] != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="شما دسترسی لازم برای این عملیات را ندارید"
                )
            
            # بررسی وجود رزرو
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
                    detail="رزرو مورد نظر یافت نشد"
                )
            
            if reservation['end_time'] <= datetime.now():
                raise HTTPException(
                    status_code=400,
                    detail="این رزرو قبلاً به پایان رسیده است"
                )
            
            async with conn.transaction():
                # پایان دادن به رزرو
                await conn.execute(
                    """
                    UPDATE reservations 
                    SET end_time = NOW(),
                        status = 'terminated_by_admin'
                    WHERE reservation_id = $1
                    """,
                    reservation_id
                )
                
                # افزایش موجودی کتاب
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
        """دریافت وضعیت کتاب شامل رزروهای فعلی و صف انتظار"""
        async with self.pool.acquire() as conn:
            # بررسی دسترسی ادمین
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                admin_username
            )
            
            if not admin or admin['role'] != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="شما دسترسی لازم برای این عملیات را ندارید"
                )
            
            # دریافت اطلاعات کتاب
            book = await conn.fetchrow(
                "SELECT * FROM books WHERE book_id = $1",
                book_id
            )
            
            if not book:
                raise HTTPException(
                    status_code=404,
                    detail="کتاب مورد نظر یافت نشد"
                )
            
            # دریافت رزروهای فعلی
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
            
            # دریافت صف انتظار
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