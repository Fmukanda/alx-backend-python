import time
import sqlite3 
import functools
import logging
import random

# Set up logging for retry mechanism
logging.basicConfig(level=logging.INFO)
connection_logger = logging.getLogger('db_connections')
retry_logger = logging.getLogger('db_retries')

def with_db_connection(func):
    """
    Decorator that automatically handles opening and closing database connections.
    Opens a connection, passes it as the first argument to the decorated function,
    and ensures the connection is properly closed afterward.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Default database name - can be made configurable
        db_name = 'users.db'
        conn = None
        
        try:
            # Open database connection
            connection_logger.info(f"Opening database connection to {db_name}")
            conn = sqlite3.connect(db_name)
            
            # Enable row factory for easier column access by name
            conn.row_factory = sqlite3.Row
            
            # Pass connection as first argument to the decorated function
            result = func(conn, *args, **kwargs)
            
            return result
            
        except Exception as e:
            # Handle any exceptions
            connection_logger.error(f"Error in {func.__name__}: {e}")
            raise e
            
        finally:
            # Always close the connection
            if conn:
                conn.close()
                connection_logger.info("Database connection closed")
    
    return wrapper

def retry_on_failure(retries=3, delay=2, backoff_factor=1.0, exceptions=(Exception,)):
    """
    Decorator that retries database operations if they fail due to transient errors.
    
    Args:
        retries (int): Maximum number of retry attempts (default: 3)
        delay (float): Initial delay between retries in seconds (default: 2)
        backoff_factor (float): Multiplier for delay after each retry (default: 1.0 for constant delay)
        exceptions (tuple): Tuple of exception types to catch and retry on (default: (Exception,))
    
    Returns:
        Decorated function that retries on failure
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries + 1):  # +1 because we include the initial attempt
                try:
                    retry_logger.info(f"Attempt {attempt + 1}/{retries + 1} for {func.__name__}")
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        retry_logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    retry_logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    
                    # If this was the last attempt, don't sleep
                    if attempt < retries:
                        retry_logger.info(f"Retrying in {current_delay:.2f} seconds...")
                        time.sleep(current_delay)
                        # Apply backoff factor for next iteration
                        current_delay *= backoff_factor
                    else:
                        retry_logger.error(f"All {retries + 1} attempts failed for {func.__name__}")
                
                except Exception as e:
                    # For exceptions not in the retry list, fail immediately
                    retry_logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    raise e
            
            # If we get here, all retries failed
            retry_logger.error(f"Function {func.__name__} failed after {retries + 1} attempts")
            raise last_exception
        
        return wrapper
    return decorator

# Specialized retry decorator for common database errors
def retry_on_db_errors(retries=3, delay=1, backoff_factor=2.0):
    """
    Specialized retry decorator for common database transient errors.
    
    Retries on:
    - sqlite3.OperationalError (database locked, etc.)
    - sqlite3.DatabaseError (general database errors)
    - sqlite3.InterfaceError (interface errors)
    """
    return retry_on_failure(
        retries=retries,
        delay=delay,
        backoff_factor=backoff_factor,
        exceptions=(sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.InterfaceError)
    )

@with_db_connection
@retry_on_failure(retries=3, delay=1)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Additional example functions with different retry strategies

@with_db_connection
@retry_on_db_errors(retries=5, delay=0.5, backoff_factor=1.5)
def fetch_user_by_id_with_db_retry(conn, user_id):
    """Fetch user by ID with specialized database error retry."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        raise ValueError(f"User with ID {user_id} not found")
    
    return result

@with_db_connection
@retry_on_failure(retries=2, delay=0.1, exceptions=(sqlite3.OperationalError,))
def insert_user_with_retry(conn, name, email, age):
    """Insert user with retry only on operational errors."""
    cursor = conn.cursor()
    
    # Simulate potential database lock by adding a small random delay
    time.sleep(random.uniform(0, 0.1))
    
    cursor.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        (name, email, age)
    )
    conn.commit()
    return cursor.lastrowid

@with_db_connection
@retry_on_failure(retries=4, delay=0.5, backoff_factor=2.0)
def update_user_with_exponential_backoff(conn, user_id, name, email):
    """Update user with exponential backoff retry strategy."""
    cursor = conn.cursor()
    
    # Simulate intermittent failure
    if random.random() < 0.6:  # 60% chance of failure for demo
        raise sqlite3.OperationalError("Simulated database lock")
    
    cursor.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (name, email, user_id)
    )
    
    if cursor.rowcount == 0:
        raise ValueError(f"No user found with ID {user_id}")
    
    conn.commit()
    return True

# Function to simulate database contention for testing
@with_db_connection
def simulate_database_lock(conn):
    """Simulate a database lock scenario for testing."""
    cursor = conn.cursor()
    
    # Begin a transaction and hold it
    cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
    time.sleep(2)  # Hold the lock for 2 seconds
    cursor.execute("SELECT COUNT(*) FROM users")
    conn.rollback()

# Helper function to setup test database
def setup_test_database():
    """Create a test database with sample data."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            credits REAL DEFAULT 100.0
        )
    ''')
    
    # Insert sample data
    sample_users = [
        ('Alice Johnson', 'alice@example.com', 28, 150.0),
        ('Bob Smith', 'bob@example.com', 32, 200.0),
        ('Carol Davis', 'carol@example.com', 25, 75.0),
        ('David Wilson', 'david@example.com', 41, 300.0),
        ('Eve Martinez', 'eve@example.com', 29, 125.0)
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO users (name, email, age, credits) VALUES (?, ?, ?, ?)", 
        sample_users
    )
    
    conn.commit()
    conn.close()
    print("Test database created with sample data!")

# Testing the retry decorator
if __name__ == "__main__":
    # Setup test database
    setup_test_database()
    
    print("\n" + "="*70)
    print("TESTING RETRY ON FAILURE DECORATOR")
    print("="*70)
    
    # Test 1: Attempt to fetch users with automatic retry on failure
    print("\n1. Testing basic retry functionality:")
    try:
        users = fetch_users_with_retry()
        print(f"Successfully fetched {len(users)} users")
        for user in users[:3]:  # Show first 3 users
            print(f"  - {user['name']} ({user['email']}) - Age: {user['age']}")
    except Exception as e:
        print(f"Failed to fetch users: {e}")
    
    # Test 2: Test retry with specific database errors
    print("\n2. Testing database-specific retry:")
    try:
        user = fetch_user_by_id_with_db_retry(user_id=1)
        print(f"Successfully fetched user: {user['name']} ({user['email']})")
    except Exception as e:
        print(f"Failed to fetch user: {e}")
    
    # Test 3: Test retry with user insertion
    print("\n3. Testing insert with retry:")
    try:
        new_user_id = insert_user_with_retry("Frank Miller", "frank@example.com", 35)
        print(f"Successfully inserted user with ID: {new_user_id}")
    except sqlite3.IntegrityError as e:
        print(f"User already exists: {e}")
    except Exception as e:
        print(f"Failed to insert user: {e}")
    
    # Test 4: Test exponential backoff retry
    print("\n4. Testing exponential backoff retry:")
    try:
        success = update_user_with_exponential_backoff(
            user_id=1, 
            name="Alice Johnson Updated", 
            email="alice.updated@example.com"
        )
        if success:
            print("Successfully updated user with exponential backoff")
    except Exception as e:
        print(f"Failed to update user: {e}")
    
    # Test 5: Test retry limits
    print("\n5. Testing retry limits (should fail after attempts):")
    
    # Create a function that always fails to test retry limits
    @with_db_connection
    @retry_on_failure(retries=2, delay=0.1)
    def always_fail_function(conn):
        raise sqlite3.OperationalError("Simulated persistent database error")
    
    try:
        always_fail_function()
    except Exception as e:
        print(f"Function failed as expected after all retries: {e}")
    
    # Test 6: Test non-retryable exceptions
    print("\n6. Testing non-retryable exceptions:")
    
    @with_db_connection
    @retry_on_failure(retries=3, delay=0.1, exceptions=(sqlite3.OperationalError,))
    def fail_with_value_error(conn):
        raise ValueError("This should not be retried")
    
    try:
        fail_with_value_error()
    except ValueError as e:
        print(f"Non-retryable exception failed immediately (as expected): {e}")
    
    # Test 7: Demonstrate backoff timing
    print("\n7. Demonstrating backoff timing:")
    
    attempt_count = 0
    
    @with_db_connection
    @retry_on_failure(retries=3, delay=0.5, backoff_factor=2.0)
    def demonstrate_backoff(conn):
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 3:  # Fail first 2 attempts
            raise sqlite3.OperationalError(f"Simulated failure #{attempt_count}")
        
        # Succeed on 3rd attempt
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        return cursor.fetchone()['count']
    
    try:
        start_time = time.time()
        count = demonstrate_backoff()
        end_time = time.time()
        print(f"Successfully got user count: {count}")
        print(f"Total time with backoff: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Backoff demonstration failed: {e}")
    
    print("\n" + "="*70)
    print("RETRY DECORATOR TESTING COMPLETE")
    print("="*70)
