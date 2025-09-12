import sqlite3
import functools
import logging
from datetime import datetime

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger specifically for database queries
db_logger = logging.getLogger('database_queries')

#### decorator to log SQL queries

def log_queries(func):
    """
    Decorator that logs SQL queries executed by any function.
    It captures and logs the query parameter before the function executes.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract query from function arguments
        # Check if 'query' is passed as keyword argument
        if 'query' in kwargs:
            query = kwargs['query']
        # Check if 'query' is the first positional argument
        elif args and len(args) > 0:
            # Assuming query is the first argument based on the function signature
            query = args[0] if isinstance(args[0], str) else None
        else:
            query = None
        
        # Log the query before execution
        if query:
            db_logger.info(f"Executing SQL query: {query.strip()}")
            # Also log function name for better traceability
            db_logger.info(f"Function: {func.__name__}")
        else:
            db_logger.warning(f"No SQL query found in function {func.__name__} arguments")
        
        # Execute the original function
        try:
            result = func(*args, **kwargs)
            db_logger.info(f"Query executed successfully, returned {len(result) if result else 0} rows")
            return result
        except Exception as e:
            db_logger.error(f"Query execution failed: {str(e)}")
            raise e
    
    return wrapper

@log_queries
def fetch_all_users(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# Create a sample database and table for testing
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
            age INTEGER
        )
    ''')
    
    # Insert sample data
    sample_users = [
        ('Alice Johnson', 'alice@example.com', 28),
        ('Bob Smith', 'bob@example.com', 32),
        ('Carol Davis', 'carol@example.com', 25),
        ('David Wilson', 'david@example.com', 41)
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)", 
        sample_users
    )
    
    conn.commit()
    conn.close()
    print("Test database created with sample data!")

# Additional examples of functions using the log_queries decorator

@log_queries
def fetch_user_by_id(query, user_id):
    """Fetch a specific user by ID."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

@log_queries
def fetch_users_by_age_range(query, min_age, max_age):
    """Fetch users within a specific age range."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query, (min_age, max_age))
    results = cursor.fetchall()
    conn.close()
    return results

@log_queries
def insert_user(query, name, email, age):
    """Insert a new user into the database."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query, (name, email, age))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

# Example usage and testing
if __name__ == "__main__":
    # Setup test database
    setup_test_database()
    
    print("\n" + "="*50)
    print("TESTING SQL QUERY LOGGING DECORATOR")
    print("="*50)
    
    # Test 1: Fetch all users while logging the query
    print("\n1. Fetching all users:")
    users = fetch_all_users(query="SELECT * FROM users")
    print(f"Found {len(users)} users")
    for user in users:
        print(f"  - ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Age: {user[3]}")
    
    # Test 2: Fetch specific user by ID
    print("\n2. Fetching user by ID:")
    user = fetch_user_by_id(
        query="SELECT * FROM users WHERE id = ?", 
        user_id=2
    )
    if user:
        print(f"Found user: {user}")
    
    # Test 3: Fetch users by age range
    print("\n3. Fetching users by age range:")
    young_users = fetch_users_by_age_range(
        query="SELECT * FROM users WHERE age BETWEEN ? AND ?",
        min_age=25,
        max_age=30
    )
    print(f"Found {len(young_users)} users between ages 25-30")
    
    # Test 4: Insert new user
    print("\n4. Inserting new user:")
    new_user_id = insert_user(
        query="INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        name="Eve Martinez",
        email="eve@example.com",
        age=29
    )
    print(f"Inserted new user with ID: {new_user_id}")
    
    # Test 5: Demonstrate error logging
    print("\n5. Testing error logging (invalid query):")
    try:
        fetch_all_users(query="SELECT * FROM nonexistent_table")
    except Exception as e:
        print(f"Caught expected error: {e}")
    
    print("\n" + "="*50)
    print("LOGGING DEMONSTRATION COMPLETE")
    print("="*50)
