from fastapi import FastAPI, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from decimal import Decimal
from services import ReservationService
from subscription_services import SubscriptionService
from admin_services import AdminService
from models import ReservationCreate, ReservationResponse, QueuePosition
from middleware import error_handler
from exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
    InsufficientFundsError,
    SubscriptionError,
    ReservationError,
    DatabaseError
)
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    generate_otp,
    SMSService,
    oauth2_scheme,
    otp_storage,
    SECRET_KEY,
    ALGORITHM
)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(error_handler)

# Database connection settings
async def init_db():
    try:
        return await asyncpg.create_pool(
            user="postgres",
            password="1497",
            database="bookstore_db",
            host="localhost"
        )
    except Exception as e:
        raise DatabaseError(f"Database connection error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    app.state.pool = await init_db()
    app.state.reservation_service = ReservationService(app.state.pool)
    app.state.subscription_service = SubscriptionService(app.state.pool)
    app.state.admin_service = AdminService(app.state.pool)

# Base Models
class Book(BaseModel):
    title: str
    isbn: str
    price: float
    genre: str
    description: str
    units: int

class User(BaseModel):
    username: str
    email: str
    password: str
    role: str = "customer"

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class OTPVerify(BaseModel):
    username: str
    otp: str

class SubscriptionUpgrade(BaseModel):
    new_model: str  # 'plus' or 'premium'
    months: Optional[int] = 1

class WalletCharge(BaseModel):
    amount: Decimal

# Helper function to validate token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")

        # Check if token is revoked
        async with app.state.pool.acquire() as conn:
            revoked = await conn.fetchrow(
                """
                SELECT * FROM revoked_tokens 
                WHERE username = $1 AND revoked_at > $2
                """,
                username, 
                datetime.fromtimestamp(payload.get("iat", 0))
            )
            
            if revoked:
                raise AuthenticationError("Token has been revoked")
                
        return username
    except JWTError:
        raise AuthenticationError("Invalid token")

# Routes (Endpoints)
@app.post("/users/")
async def create_user(user: User):
    try:
        async with app.state.pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT username FROM users WHERE username = $1",
                user.username
            )
            if existing_user:
                raise ValidationError(
                    message="This username is already registered",
                    details={"username": user.username}
                )
            
            hashed_password = get_password_hash(user.password)
            
            await conn.execute(
                """
                INSERT INTO users (username, email, password, role)
                VALUES ($1, $2, $3, $4)
                """,
                user.username, user.email, hashed_password, user.role
            )
            
            user_id = await conn.fetchval(
                "SELECT user_id FROM users WHERE username = $1",
                user.username
            )
            
            await conn.execute(
                """
                INSERT INTO customers (user_id, subscription_model, wallet)
                VALUES ($1, 'free', 100000)
                """,
                user_id
            )
            
    except asyncpg.exceptions.UniqueViolationError:
        raise ValidationError("This email or username is already registered")
    except asyncpg.exceptions.DataError as e:
        raise ValidationError(f"Invalid data: {str(e)}")
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise ValidationError("Error in foreign key reference")
    except asyncpg.exceptions.PostgresError as e:
        raise DatabaseError(f"Database error: {str(e)}")
    
    return {"message": "User created successfully"}

@app.post("/login/")
async def login(user_data: UserLogin):
    try:
        async with app.state.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE username = $1",
                user_data.username
            )

        if not user or not verify_password(user_data.password, user['password']):
            raise AuthenticationError("Incorrect username or password")

        otp = generate_otp()
        otp_storage[user_data.username] = otp
        
        sms_service = SMSService()
        sms_service.send_sms("Phone number", f"Your verification code: {otp}")
        
        return {"message": "Verification code sent to your phone number"}
    except Exception as e:
        raise DatabaseError(f"Login error: {str(e)}")

@app.post("/verify-otp/", response_model=Token)
async def verify_otp(otp_data: OTPVerify):
    stored_otp = otp_storage.get(otp_data.username)
    
    if not stored_otp or stored_otp != otp_data.otp:
        raise AuthenticationError("Invalid verification code")
    
    del otp_storage[otp_data.username]
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": otp_data.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/books/")
async def create_book(book: Book, username: str = Depends(get_current_user)):
    try:
        async with app.state.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                username
            )
            if user['role'] != 'admin':
                raise AuthorizationError("You do not have the necessary permissions for this operation")
                
            existing_book = await conn.fetchrow(
                "SELECT * FROM books WHERE isbn = $1",
                book.isbn
            )
            if existing_book:
                raise ValidationError(
                    message="A book with this ISBN is already registered",
                    details={"isbn": book.isbn}
                )
            
            await conn.execute(
                """
                INSERT INTO books (title, isbn, price, genre, description, units)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                book.title, book.isbn, book.price, book.genre,
                book.description, book.units
            )
    except asyncpg.exceptions.UniqueViolationError:
        raise ValidationError("This ISBN is already registered")
    except asyncpg.exceptions.DataError as e:
        raise ValidationError(f"Invalid data: {str(e)}")
    except Exception as e:
        raise DatabaseError(f"Error in registering book: {str(e)}")
        
    return {"message": "Book registered successfully"}

@app.get("/books/")
async def get_books(username: str = Depends(get_current_user)):
    try:
        async with app.state.pool.acquire() as conn:
            books = await conn.fetch("SELECT * FROM books")
        return books
    except Exception as e:
        raise DatabaseError(f"Error in retrieving book list: {str(e)}")

@app.post("/reservations/", response_model=ReservationResponse)
async def create_reservation(
    reservation: ReservationCreate,
    username: str = Depends(get_current_user)
):
    try:
        async with app.state.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT c.customer_id 
                FROM customers c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.username = $1
                """,
                username
            )
            
            if not customer:
                raise ResourceNotFoundError(
                    message="Customer not found",
                    details={"username": username}
                )
            
            result = await app.state.reservation_service.create_reservation(
                customer['customer_id'],
                reservation.book_id,
                reservation.days
            )
            
            return result
    except InsufficientFundsError as e:
        raise InsufficientFundsError(
            message="Insufficient funds",
            details={"required": e.details.get("required"),
                    "current_balance": e.details.get("current_balance")}
        )
    except ReservationError as e:
        raise ReservationError(
            message="Error in reserving book",
            details=e.details
        )
    except Exception as e:
        raise DatabaseError(f"Error in creating reservation: {str(e)}")

@app.post("/subscription/upgrade/")
async def upgrade_subscription(
    upgrade_data: SubscriptionUpgrade,
    username: str = Depends(get_current_user)
):
    try:
        async with app.state.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT c.customer_id 
                FROM customers c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.username = $1
                """,
                username
            )
            
            if not customer:
                raise ResourceNotFoundError(
                    message="Customer not found",
                    details={"username": username}
                )
                
            result = await app.state.subscription_service.upgrade_subscription(
                customer['customer_id'],
                upgrade_data.new_model,
                upgrade_data.months
            )
            return result
    except InsufficientFundsError as e:
        raise InsufficientFundsError(
            message="Insufficient funds",
            details=e.details
        )
    except SubscriptionError as e:
        raise SubscriptionError(
            message="Error in upgrading subscription",
            details=e.details
        )
    except Exception as e:
        raise DatabaseError(f"Error in upgrading subscription: {str(e)}")

@app.post("/wallet/charge/")
async def charge_wallet(
    charge_data: WalletCharge,
    username: str = Depends(get_current_user)
):
    try:
        async with app.state.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT c.customer_id 
                FROM customers c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.username = $1
                """,
                username
            )
            
            if not customer:
                raise ResourceNotFoundError(
                    message="Customer not found",
                    details={"username": username}
                )
                
            result = await app.state.subscription_service.add_wallet_balance(
                customer['customer_id'],
                charge_data.amount
            )
            return result
    except ValidationError as e:
        raise ValidationError(
            message="Invalid charge amount",
            details=e.details
        )
    except Exception as e:
        raise DatabaseError(f"Error in charging wallet: {str(e)}")

@app.get("/subscription/info/")
async def get_subscription_info(username: str = Depends(get_current_user)):
    try:
        async with app.state.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT c.customer_id 
                FROM customers c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.username = $1
                """,
                username
            )
            
            if not customer:
                raise ResourceNotFoundError(
                    message="Customer not found",
                    details={"username": username}
                )
                
            return await app.state.subscription_service.get_subscription_info(
                customer['customer_id']
            )
    except Exception as e:
        raise DatabaseError(f"Error in retrieving subscription info: {str(e)}")

@app.get("/wallet/balance/")
async def get_wallet_balance(username: str = Depends(get_current_user)):
    try:
        async with app.state.pool.acquire() as conn:
            customer = await conn.fetchrow(
                """
                SELECT c.customer_id 
                FROM customers c
                JOIN users u ON c.user_id = u.user_id
                WHERE u.username = $1
                """,
                username
            )
            
            if not customer:
                raise ResourceNotFoundError(
                    message="Customer not found",
                    details={"username": username}
                )
                
            return {
                "balance": await app.state.subscription_service.get_wallet_balance(
                    customer['customer_id']
                )
            }
    except Exception as e:
        raise DatabaseError(f"Error in retrieving wallet balance: {str(e)}")

@app.post("/admin/revoke-token/{username}")
async def revoke_user_token(
    username: str,
    current_user: str = Depends(get_current_user)
):
    """Revoke a user's token"""
    try:
        async with app.state.pool.acquire() as conn:
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                current_user
            )
            if admin['role'] != 'admin':
                raise AuthorizationError(
                    message="You do not have the necessary permissions for this operation",
                    details={"required_role": "admin"}
                )
                
            target_user = await conn.fetchrow(
                "SELECT username FROM users WHERE username = $1",
                username
            )
            if not target_user:
                raise ResourceNotFoundError(
                    message="User not found",
                    details={"username": username}
                )
            
            result = await app.state.admin_service.revoke_user_token(
                current_user,
                username
            )
            return {"message": "User token revoked successfully"}
    except (AuthorizationError, ResourceNotFoundError) as e:
        raise e
    except Exception as e:
        raise DatabaseError(f"Error in revoking user token: {str(e)}")

@app.post("/admin/end-reservation/{reservation_id}")
async def end_reservation(
    reservation_id: int,
    current_user: str = Depends(get_current_user)
):
    """End a reservation"""
    try:
        async with app.state.pool.acquire() as conn:
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                current_user
            )
            if admin['role'] != 'admin':
                raise AuthorizationError(
                    message="You do not have the necessary permissions for this operation",
                    details={"required_role": "admin"}
                )
            
            reservation = await conn.fetchrow(
                "SELECT * FROM reservations WHERE reservation_id = $1",
                reservation_id
            )
            if not reservation:
                raise ResourceNotFoundError(
                    message="Reservation not found",
                    details={"reservation_id": reservation_id}
                )
            
            result = await app.state.admin_service.end_reservation(
                current_user,
                reservation_id
            )
            return {"message": "Reservation ended successfully"}
    except (AuthorizationError, ResourceNotFoundError) as e:
        raise e
    except Exception as e:
        raise DatabaseError(f"Error in ending reservation: {str(e)}")

@app.get("/admin/book-status/{book_id}")
async def get_book_status(
    book_id: int,
    current_user: str = Depends(get_current_user)
):
    """Get the full status of a book"""
    try:
        async with app.state.pool.acquire() as conn:
            admin = await conn.fetchrow(
                "SELECT role FROM users WHERE username = $1",
                current_user
            )
            if admin['role'] != 'admin':
                raise AuthorizationError(
                    message="You do not have the necessary permissions for this operation",
                    details={"required_role": "admin"}
                )
            
            book = await conn.fetchrow(
                "SELECT * FROM books WHERE book_id = $1",
                book_id
            )
            if not book:
                raise ResourceNotFoundError(
                    message="Book not found",
                    details={"book_id": book_id}
                )
            
            return await app.state.admin_service.get_book_status(
                current_user,
                book_id
            )
    except (AuthorizationError, ResourceNotFoundError) as e:
        raise e
    except Exception as e:
        raise DatabaseError(f"Error in retrieving book status: {str(e)}")

@app.get("/test-auth/")
async def test_auth(username: str = Depends(get_current_user)):
    """Test endpoint to validate token"""
    try:
        return {"message": "Token is valid", "username": username}
    except Exception as e:
        raise AuthenticationError("Error in validating token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)