CREATE TABLE reservations (
    reservation_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    book_id INT REFERENCES books(book_id),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    price DECIMAL(10, 2)
);