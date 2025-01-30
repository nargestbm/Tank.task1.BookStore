from fastapi import HTTPException
import asyncpg
from datetime import datetime
from typing import List, Optional

class CityService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_city(self, name: str, province: str, country: str = "Iran") -> dict:
        async with self.pool.acquire() as conn:
            try:
                city = await conn.fetchrow(
                    """
                    INSERT INTO cities (name, province, country)
                    VALUES ($1, $2, $3)
                    RETURNING *
                    """,
                    name, province, country
                )
                return dict(city)
            except asyncpg.UniqueViolationError:
                raise HTTPException(status_code=400, detail="این شهر قبلاً ثبت شده است")

    async def get_cities(self, skip: int = 0, limit: int = 10) -> List[dict]:
        async with self.pool.acquire() as conn:
            cities = await conn.fetch(
                """
                SELECT * FROM cities
                ORDER BY name
                LIMIT $1 OFFSET $2
                """,
                limit, skip
            )
            return [dict(city) for city in cities]

    async def get_city(self, city_id: int) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            city = await conn.fetchrow(
                "SELECT * FROM cities WHERE city_id = $1",
                city_id
            )
            return dict(city) if city else None

    async def update_city(self, city_id: int, name: str = None, 
                         province: str = None, country: str = None) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            # ساخت کوئری داینامیک برای آپدیت
            updates = []
            values = []
            if name is not None:
                updates.append("name = $1")
                values.append(name)
            if province is not None:
                updates.append(f"province = ${len(values) + 1}")
                values.append(province)
            if country is not None:
                updates.append(f"country = ${len(values) + 1}")
                values.append(country)

            if not updates:
                return await self.get_city(city_id)

            values.append(city_id)
            query = f"""
                UPDATE cities
                SET {', '.join(updates)}
                WHERE city_id = ${len(values)}
                RETURNING *
            """
            
            city = await conn.fetchrow(query, *values)
            if not city:
                raise HTTPException(status_code=404, detail="شهر مورد نظر یافت نشد")
            return dict(city)

    async def delete_city(self, city_id: int) -> bool:
        async with self.pool.acquire() as conn:
            # بررسی استفاده از شهر در جدول نویسندگان
            author_count = await conn.fetchval(
                "SELECT COUNT(*) FROM authors WHERE city_id = $1",
                city_id
            )
            if author_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="این شهر به نویسندگان مرتبط است و نمی‌تواند حذف شود"
                )

            result = await conn.execute(
                "DELETE FROM cities WHERE city_id = $1",
                city_id
            )
            return 'DELETE 1' in result

class GenreService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_genre(self, name: str, description: Optional[str] = None) -> dict:
        async with self.pool.acquire() as conn:
            try:
                genre = await conn.fetchrow(
                    """
                    INSERT INTO genres (name, description)
                    VALUES ($1, $2)
                    RETURNING *
                    """,
                    name, description
                )
                return dict(genre)
            except asyncpg.UniqueViolationError:
                raise HTTPException(status_code=400, detail="این ژانر قبلاً ثبت شده است")

    async def get_genres(self, skip: int = 0, limit: int = 10) -> List[dict]:
        async with self.pool.acquire() as conn:
            genres = await conn.fetch(
                """
                SELECT * FROM genres
                ORDER BY name
                LIMIT $1 OFFSET $2
                """,
                limit, skip
            )
            return [dict(genre) for genre in genres]

    async def get_genre(self, genre_id: int) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            genre = await conn.fetchrow(
                "SELECT * FROM genres WHERE genre_id = $1",
                genre_id
            )
            return dict(genre) if genre else None

    async def update_genre(self, genre_id: int, 
                          name: Optional[str] = None, 
                          description: Optional[str] = None) -> dict:
        async with self.pool.acquire() as conn:
            # ساخت کوئری داینامیک برای آپدیت
            updates = []
            values = []
            if name is not None:
                updates.append("name = $1")
                values.append(name)
            if description is not None:
                updates.append(f"description = ${len(values) + 1}")
                values.append(description)

            if not updates:
                return await self.get_genre(genre_id)

            values.append(genre_id)
            query = f"""
                UPDATE genres
                SET {', '.join(updates)}
                WHERE genre_id = ${len(values)}
                RETURNING *
            """
            
            try:
                genre = await conn.fetchrow(query, *values)
                if not genre:
                    raise HTTPException(status_code=404, detail="ژانر مورد نظر یافت نشد")
                return dict(genre)
            except asyncpg.UniqueViolationError:
                raise HTTPException(status_code=400, detail="این نام ژانر قبلاً ثبت شده است")

    async def delete_genre(self, genre_id: int) -> bool:
        async with self.pool.acquire() as conn:
            # بررسی استفاده از ژانر در جدول کتاب‌ها
            book_count = await conn.fetchval(
                "SELECT COUNT(*) FROM books WHERE genre = $1",
                genre_id
            )
            if book_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="این ژانر به کتاب‌ها مرتبط است و نمی‌تواند حذف شود"
                )

            result = await conn.execute(
                "DELETE FROM genres WHERE genre_id = $1",
                genre_id
            )
            return 'DELETE 1' in result

class AuthorService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_author(self, user_id: int, city_id: int,
                          bank_account_number: str,
                          goodreads_link: Optional[str] = None,
                          bio: Optional[str] = None) -> dict:
        async with self.pool.acquire() as conn:
            # بررسی وجود کاربر
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
            if not user:
                raise HTTPException(status_code=404, detail="کاربر مورد نظر یافت نشد")

            # بررسی وجود شهر
            city = await conn.fetchrow(
                "SELECT * FROM cities WHERE city_id = $1",
                city_id
            )
            if not city:
                raise HTTPException(status_code=404, detail="شهر مورد نظر یافت نشد")

            try:
                author = await conn.fetchrow(
                    """
                    INSERT INTO authors (user_id, city_id, bank_account_number, 
                                       goodreads_link, bio)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                    """,
                    user_id, city_id, bank_account_number, goodreads_link, bio
                )
                
                # تغییر نقش کاربر به نویسنده
                await conn.execute(
                    """
                    UPDATE users 
                    SET role = 'author'
                    WHERE user_id = $1
                    """,
                    user_id
                )
                
                return {
                    **dict(author),
                    'user': dict(user),
                    'city': dict(city)
                }
            except asyncpg.UniqueViolationError:
                raise HTTPException(
                    status_code=400,
                    detail="این کاربر قبلاً به عنوان نویسنده ثبت شده است"
                )

    async def get_authors(self, skip: int = 0, limit: int = 10) -> List[dict]:
        async with self.pool.acquire() as conn:
            authors = await conn.fetch(
                """
                SELECT a.*, 
                       row_to_json(u.*) as user,
                       row_to_json(c.*) as city
                FROM authors a
                JOIN users u ON a.user_id = u.user_id
                JOIN cities c ON a.city_id = c.city_id
                ORDER BY u.username
                LIMIT $1 OFFSET $2
                """,
                limit, skip
            )
            return [dict(author) for author in authors]

    async def get_author(self, author_id: int) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            author = await conn.fetchrow(
                """
                SELECT a.*, 
                       row_to_json(u.*) as user,
                       row_to_json(c.*) as city
                FROM authors a
                JOIN users u ON a.user_id = u.user_id
                JOIN cities c ON a.city_id = c.city_id
                WHERE a.author_id = $1
                """,
                author_id
            )
            return dict(author) if author else None

    async def update_author(self, author_id: int, 
                          city_id: Optional[int] = None,
                          bank_account_number: Optional[str] = None,
                          goodreads_link: Optional[str] = None,
                          bio: Optional[str] = None) -> dict:
        async with self.pool.acquire() as conn:
            # ساخت کوئری داینامیک برای آپدیت
            updates = []
            values = []
            
            if city_id is not None:
                # بررسی وجود شهر
                city = await conn.fetchrow(
                    "SELECT * FROM cities WHERE city_id = $1",
                    city_id
                )
                if not city:
                    raise HTTPException(status_code=404, detail="شهر مورد نظر یافت نشد")
                updates.append("city_id = $1")
                values.append(city_id)
                
            if bank_account_number is not None:
                updates.append(f"bank_account_number = ${len(values) + 1}")
                values.append(bank_account_number)
                
            if goodreads_link is not None:
                updates.append(f"goodreads_link = ${len(values) + 1}")
                values.append(goodreads_link)
                
            if bio is not None:
                updates.append(f"bio = ${len(values) + 1}")
                values.append(bio)

            if not updates:
                return await self.get_author(author_id)

            values.append(author_id)
            query = f"""
                UPDATE authors
                SET {', '.join(updates)}
                WHERE author_id = ${len(values)}
                RETURNING *
            """
            
            author = await conn.fetchrow(query, *values)
            if not author:
                raise HTTPException(status_code=404, detail="نویسنده مورد نظر یافت نشد")
            
            # دریافت اطلاعات کامل نویسنده
            return await self.get_author(author_id)

    async def delete_author(self, author_id: int) -> bool:
        async with self.pool.acquire() as conn:
            # بررسی وجود کتاب‌های مرتبط با نویسنده
            books = await conn.fetchval(
                """
                SELECT COUNT(*) 
                FROM book_authors 
                WHERE author_id = $1
                """,
                author_id
            )
            if books > 0:
                raise HTTPException(
                    status_code=400,
                    detail="این نویسنده دارای کتاب‌های منتشر شده است و نمی‌تواند حذف شود"
                )

            # دریافت user_id نویسنده قبل از حذف
            author = await conn.fetchrow(
                "SELECT user_id FROM authors WHERE author_id = $1",
                author_id
            )
            if not author:
                raise HTTPException(status_code=404, detail="نویسنده مورد نظر یافت نشد")

            async with conn.transaction():
                # حذف نویسنده
                result = await conn.execute(
                    "DELETE FROM authors WHERE author_id = $1",
                    author_id
                )
                
                # تغییر نقش کاربر به customer (در صورتی که نویسنده حذف شد)
                if 'DELETE 1' in result:
                    await conn.execute(
                        """
                        UPDATE users 
                        SET role = 'customer'
                        WHERE user_id = $1
                        """,
                        author['user_id']
                    )
                    return True
                
                return False