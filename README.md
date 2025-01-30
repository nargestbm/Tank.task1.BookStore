# BookStore Management System
## OverviewA comprehensive FastAPI-based bookstore management system that handles user authentication, book reservations, subscription management, and administrative operations. The system implements a sophisticated user role system, wallet functionality, and a queue-based reservation system.
## Features
### User Management
- User registration and authentication with JWT tokens- Two-factor authentication using OTP
- Role-based access control (Customer, Author, Admin)- User profile management
### Book Management
- Comprehensive book catalog with detailed information- ISBN-based book tracking
- Multi-author support- Genre categorization
- Inventory management
### Reservation System- Smart queue-based reservation system
- Priority-based allocation for premium users- Flexible reservation duration based on subscription type
- Automatic inventory management
### Subscription System- Three-tier subscription model (Free, Plus, Premium)
- Subscription benefits:  - Plus: Up to 7 days reservation, 5 simultaneous books
  - Premium: Up to 14 days reservation, 10 simultaneous books- Automatic renewal system
- Special discounts for frequent readers
### Payment and Wallet- Built-in wallet system
- Secure transaction handling- Automatic price calculation based on subscription type
- Special discounts for Plus subscribers
### Author Management- Author profile management
- City-based author tracking- Goodreads integration support
- Banking information management
### Administrative Features
- Token revocation- Reservation management
- Book status monitoring- Comprehensive error handling
## Technical Stack
### Backend
- FastAPI- PostgreSQL
- asyncpg for async database operations- JWT for authentication
- Pydantic for data validation
### Security- OAuth2 implementation
- Password hashing with bcrypt- Two-factor authentication
- Role-based access control
## Database Schema
### Core Tables```sql
users- user_id (PK)
- username- email
- password- role
books
- book_id (PK)- title
- isbn- price
- genre- description
- units
customers- customer_id (PK)
- user_id (FK)- subscription_model
- subscription_end_time- wallet
authors
- author_id (PK)- user_id (FK)
- city
- goodreads_link- bank_account_number
- bio```
## Setup and Installation
1. Clone the repository
cd Tank.task1.BookStore
2. Create and activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install dependencies

4. Set up PostgreSQL database```bash
# Create databasecreatedb bookstore_db
# Run SQL scripts
psql -d bookstore_db -f database/schema.sql```

5. Configure environment variables```bash
cp .env.example .env# Edit .env with your database credentials and JWT secret
6. Run the application
```bashuvicorn main:app --reload
## API Documentation
After running the application, access the API documentation at:- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
## Error Handling
The system implements comprehensive error handling with custom exceptions:- AuthenticationError
- AuthorizationError- ResourceNotFoundError
- ValidationError- InsufficientFundsError
- SubscriptionError
- ReservationError
- DatabaseError
## Contributing
1. Fork the repository2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
## License
This project is licensed under the MIT License - see the LICENSE file for details.