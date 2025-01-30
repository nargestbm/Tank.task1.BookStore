# FastAPI Bookstore API

A FastAPI-based RESTful API for managing a digital bookstore with features including user authentication, book reservations, subscription management, and administrative controls.

## Features

- User Authentication with OTP verification
- Book management and reservations
- Tiered subscription system (Free, Plus, Premium)
- Wallet system for payments
- Queue management for book reservations
- Admin controls for user and reservation management
- City, Genre, and Author management

## Prerequisites

- Python 3.7+
- PostgreSQL 12+
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bookstore-api
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install required packages:
```bash
pip install fastapi uvicorn[standard] asyncpg python-jose[cryptography] passlib[bcrypt] pydantic[email] python-multipart
```

## Database Setup

1. Create a new PostgreSQL database:
```sql
CREATE DATABASE bookstore_db;
```

2. Import your existing PostgreSQL tables using the SQL files:
```bash
psql -U postgres -d bookstore_db -f path/to/your/sql/files.sql
```

3. Update database connection settings in `main.py` if needed:
```python
async def init_db():
    return await asyncpg.create_pool(
        user="postgres",
        password="1497",
        database="bookstore_db",
        host="localhost"
    )
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

2. Access the interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication
- POST `/users/` - Create new user
- POST `/login/` - Login with username/password
- POST `/verify-otp/` - Verify OTP and get access token

### Books
- POST `/books/` - Create new book (Admin only)
- GET `/books/` - Get all books

### Reservations
- POST `/reservations/` - Create new reservation
- GET `/admin/book-status/{book_id}` - Get book reservation status (Admin only)
- POST `/admin/end-reservation/{reservation_id}` - End reservation (Admin only)

### Subscription
- POST `/subscription/upgrade/` - Upgrade subscription
- GET `/subscription/info/` - Get subscription information
- POST `/wallet/charge/` - Add funds to wallet
- GET `/wallet/balance/` - Get wallet balance

### Admin Controls
- POST `/admin/revoke-token/{username}` - Revoke user token
- GET `/admin/book-status/{book_id}` - Get book status

### Cities, Genres, and Authors
- Complete CRUD operations for managing cities, genres, and authors

## Project Structure

```
bookstore-api/
├── main.py                 # FastAPI application and routes
├── auth.py                 # Authentication logic
├── services.py            # Reservation service
├── admin_services.py      # Admin functionality
├── subscription_services.py # Subscription management
├── crud_services.py       # CRUD operations for cities, genres, authors
├── models.py              # Pydantic models
├── exceptions.py          # Custom exceptions
└── middleware.py          # Error handling middleware
```

## Error Handling

The application uses custom exceptions defined in `exceptions.py` and handles them through the middleware in `middleware.py`. Errors are logged to `error.log`.

## Security

- JWT-based authentication
- OTP verification for login
- Role-based access control
- Token revocation capabilities

## Subscription Tiers

1. Free
   - Cannot make reservations
   - Basic access to book catalog

2. Plus (50,000 tomans monthly)
   - Up to 5 simultaneous reservations
   - Maximum 7-day reservation period
   - Discount after reading 3 books per month

3. Premium (200,000 tomans monthly)
   - Up to 10 simultaneous reservations
   - Maximum 14-day reservation period
   - Priority in reservation queue

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request


