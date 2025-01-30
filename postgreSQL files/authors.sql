CREATE TABLE authors (
    author_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    city VARCHAR(50),
    goodreads_link VARCHAR(200),
    bank_account_number VARCHAR(50),
    bio TEXT
);
