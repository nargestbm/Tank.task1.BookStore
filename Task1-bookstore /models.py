from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum

# مدل‌های قبلی
class SubscriptionType(str, Enum):
    FREE = "free"
    PLUS = "plus"
    PREMIUM = "premium"

class ReservationCreate(BaseModel):
    book_id: int
    days: int

class ReservationResponse(BaseModel):
    reservation_id: int
    book_id: int
    customer_id: int
    start_time: datetime
    end_time: datetime
    price: float
    status: str

class QueuePosition(BaseModel):
    position: int
    estimated_wait: Optional[str]

# مدل‌های جدید
class CityBase(BaseModel):
    name: str
    province: str
    country: str = "Iran"

class CityCreate(CityBase):
    pass

class CityResponse(CityBase):
    city_id: int
    created_at: datetime

class GenreBase(BaseModel):
    name: str
    description: Optional[str] = None

class GenreCreate(GenreBase):
    pass

class GenreResponse(GenreBase):
    genre_id: int
    created_at: datetime

class AuthorBase(BaseModel):
    city_id: int
    goodreads_link: Optional[str]
    bank_account_number: str
    bio: Optional[str]

class AuthorCreate(AuthorBase):
    user_id: int

class AuthorUpdate(BaseModel):
    city_id: Optional[int]
    goodreads_link: Optional[str]
    bank_account_number: Optional[str]
    bio: Optional[str]

class AuthorResponse(AuthorBase):
    author_id: int
    user: dict  # اطلاعات کاربری نویسنده
    city: dict  # اطلاعات شهر نویسنده