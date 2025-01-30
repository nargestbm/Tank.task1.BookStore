# Bookstore API Documentation

## Overview
This project implements a RESTful API for a bookstore management system using FastAPI and PostgreSQL. The system handles book reservations, user subscriptions, and administrative functions with a focus on security and scalability.

## Key Features
- User authentication with JWT and OTP verification
- Tiered subscription system (Free, Plus, Premium)
- Book reservation system with queuing
- Wallet-based payment system
- Administrative controls
- City and genre management
- Author profile management

## Technical Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL with asyncpg
- **Authentication**: JWT + OTP
- **API Security**: OAuth2 with Bearer token
- **Error Handling**: Custom exception hierarchy
- **Database Migration**: SQL scripts

## Database Schema
### Core Tables
1. **users**
   - Primary user information
   - Role-based access control
   - Unique constraints on username and email

2. **customers**
   - Subscription management
   - Wallet balance
   - Connected to users via foreign key

3. **books**
   - Book inventory management
   - ISBN uniqueness enforcement
   - Price and units tracking

4. **reservations**
   - Tracks book borrowing
   - Start and end times
   - Price information

### Supporting Tables
1. **authors**
   - Author profile management
   - Banking information
   - Social media links

2. **cities**
   - Location management
   - Province and country tracking

3. **genres**
   - Book categorization
   - Description storage

4. **book_authors**
   - Many-to-many relationship between books and authors

## Service Architecture

### Core Services
1. **ReservationService**
   - Handles book reservations
   - Implements queuing system
   - Price calculation based on subscription
   - Availability checking

2. **SubscriptionService**
   - Subscription management (Free/Plus/Premium)
   - Wallet operations
   - Subscription renewal
   - Balance checking

3. **AdminService**
   - Token revocation
   - Reservation management
   - Book status monitoring
   - Administrative operations

### Supporting Services
1. **CityService**
   - City CRUD operations
   - Location management
   - Validation checks

2. **GenreService**
   - Genre CRUD operations
   - Category management
   - Usage tracking

3. **AuthorService**
   - Author profile management
   - Bank account handling
   - Role management

## API Endpoints

### Authentication
- POST `/users/`: User registration
- POST `/login/`: User login with OTP
- POST `/verify-otp/`: OTP verification

### Book Management
- POST `/books/`: Add new book (Admin)
- GET `/books/`: List all books

### Reservations
- POST `/reservations/`: Create reservation
- GET `/admin/book-status/{book_id}`: Get book status (Admin)
- POST `/admin/end-reservation/{reservation_id}`: End reservation (Admin)

### Subscription
- POST `/subscription/upgrade/`: Upgrade subscription
- GET `/subscription/info/`: Get subscription info
- GET `/wallet/balance/`: Get wallet balance
- POST `/wallet/charge/`: Add funds to wallet

### Administrative
- POST `/admin/revoke-token/{username}`: Revoke user token
- GET `/test-auth/`: Test authentication

## Security Features

### Authentication Flow
1. User registration with password hashing
2. Login attempt triggers OTP generation
3. OTP verification generates JWT token
4. JWT token used for subsequent requests

### Authorization
- Role-based access control
- Token revocation capabilities
- Resource access validation
- Custom error handling

### Data Protection
- Password hashing with bcrypt
- JWT token encryption
- Secure token storage
- SQL injection prevention

## Error Handling
Custom exception hierarchy:
- BookStoreException (Base)
- AuthenticationError
- AuthorizationError
- ResourceNotFoundError
- ValidationError
- InsufficientFundsError
- SubscriptionError
- ReservationError
- DatabaseError

## Subscription Tiers

### Free Tier
- Basic access
- No reservation privileges
- Limited functionality

### Plus Tier
- Up to 5 simultaneous reservations
- 7-day maximum reservation period
- Volume discounts available

### Premium Tier
- Up to 10 simultaneous reservations
- 14-day maximum reservation period
- Priority in reservation queue
- Enhanced pricing benefits

## Best Practices Implemented
1. **Code Organization**
   - Modular service architecture
   - Clear separation of concerns
   - Consistent error handling

2. **Security**
   - OTP verification
   - JWT authentication
   - Role-based access

3. **Database**
   - Proper indexing
   - Foreign key constraints
   - Transaction management

4. **API Design**
   - RESTful principles
   - Consistent error responses
   - Clear endpoint structure

## Deployment Considerations
1. **Database Setup**
   - Execute provided SQL scripts
   - Set up proper indexes
   - Configure connection pool

2. **Environment Configuration**
   - JWT secret key
   - Database credentials
   - SMS service setup

3. **Security Settings**
   - CORS configuration
   - Rate limiting
   - Error logging

## Future Improvements
1. **Technical Enhancements**
   - Caching implementation
   - Rate limiting
   - API documentation (Swagger/OpenAPI)
   - Automated testing suite

2. **Feature Additions**
   - Book recommendations
   - Rating system
   - Review management
   - Report generation

3. **Security Upgrades**
   - Rate limiting
   - IP blocking
   - Enhanced audit logging
   - Session management
