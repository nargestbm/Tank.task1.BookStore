DROP TABLE IF EXISTS revoked_tokens;

CREATE TABLE revoked_tokens (
    token_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    revoked_at TIMESTAMP NOT NULL,
    revoked_by INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (revoked_by) REFERENCES users(user_id)
);

CREATE INDEX idx_revoked_tokens_user_id ON revoked_tokens(user_id);