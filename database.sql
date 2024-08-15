CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    endpoint TEXT,
    request_count INTEGER DEFAULT 0,
    last_request TIMESTAMP
);
