from flask import Flask, request, jsonify, g
import psycopg2
from datetime import datetime, timedelta

app = Flask(__name__)

# Database connection
def get_db_connection():
    if 'db' not in g:
        g.db = psycopg2.connect(
            dbname='your_db_name',
            user='your_db_user',
            password='your_db_password',
            host='your_db_host'
        )
    return g.db

@app.teardown_appcontext
def close_db_connection(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Rate limit configuration
RATE_LIMITS = {
    'default': {'limit': 10, 'window': timedelta(minutes=1)},
    '/api/special': {'limit': 5, 'window': timedelta(minutes=1)},
}

def check_rate_limit(user_id, endpoint):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the endpoint-specific or default rate limit
    rate_limit = RATE_LIMITS.get(endpoint, RATE_LIMITS['default'])
    limit = rate_limit['limit']
    window = rate_limit['window']

    # Get the current time and calculate the window start time
    now = datetime.now()
    window_start = now - window

    # Check request count for the user and endpoint
    cursor.execute("""
        SELECT request_count, last_request 
        FROM rate_limits 
        WHERE user_id = %s AND endpoint = %s
    """, (user_id, endpoint))
    row = cursor.fetchone()

    if row:
        request_count, last_request = row
        if last_request < window_start:
            # Reset the count if outside the current window
            request_count = 0
        if request_count >= limit:
            return False

        # Update the request count and last request time
        cursor.execute("""
            UPDATE rate_limits
            SET request_count = request_count + 1, last_request = %s
            WHERE user_id = %s AND endpoint = %s
        """, (now, user_id, endpoint))
    else:
        # Insert a new record if not exists
        cursor.execute("""
            INSERT INTO rate_limits (user_id, endpoint, request_count, last_request)
            VALUES (%s, %s, %s, %s)
        """, (user_id, endpoint, 1, now))

    conn.commit()
    cursor.close()
    return True

# Middleware for rate limiting
@app.before_request
def rate_limit():
    user_id = request.headers.get('X-User-ID', 'anonymous')
    endpoint = request.path

    if not check_rate_limit(user_id, endpoint):
        return jsonify({"error": "Rate limit exceeded"}), 429

# Example endpoint
@app.route('/api/data')
def get_data():
    return jsonify({"data": "This is your data"})

# Another endpoint with a different rate limit
@app.route('/api/special')
def get_special_data():
    return jsonify({"data": "This is your special data"})

if __name__ == '__main__':
    app.run(debug=True)
