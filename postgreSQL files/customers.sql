CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    subscription_model VARCHAR(20),
    subscription_end_time TIMESTAMP,
    wallet_money DECIMAL(10, 2),
    wallet DECIMAL(10, 2)
);