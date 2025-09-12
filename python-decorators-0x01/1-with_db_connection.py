import sqlite3 
import functools
import logging

# Set up logging for connection management
logging.basicConfig(level=logging.INFO)
connection_logger = logging.getLogger('db_connections')

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
            
            # Commit any pending transactions
            conn.commit()
            connection_logger.info("Database transaction committed successfully")
            
            return result
            
        except sqlite3.Error as e:
            # Handle database-specific errors
            connection_logger.error(f"Database error in {func.__name__}: {e}")
            if conn:
                conn.rollback()
                connection_logger.info("Database transaction rolled back")
            raise e
            
        except Exception as e:
            # Handle any other exceptions
            connection_logger.error(f"Error in {func.__name__}: {e}")
            if conn:
                conn.rollback()
                connection_logger.info("Database transaction rolled back")
            raise e
            
        finally:
            # Always close the connection
            if conn:
                conn.close()
                connection_logger.info("Database connection closed")
    
    return wrapper

@with_db_connection 
def get_user_by_id(conn, user_id): 
    cursor = conn.cursor() 
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)) 
    return cursor.fetchone()

# Additional example functions using the decorator

@with_db_connection
def get_all_users(conn):
    """Fetch all users from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

@with_db_connection
def create_user(conn, name, email, age):
    """Create a new user in the database."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        (name, email, age)
    )
    return cursor.lastrowid

@with_db_connection
def update_user_email(conn, user_id, new_email):
    """Update a user's email address."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET email = ? WHERE id = ?",
        (new_email, user_id)
    )
    return cursor.rowcount > 0  # Return True if user was updated

@with_db_connection
def delete_user(conn, user_id):
    """Delete a user from the database."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return cursor.rowcount > 0  # Return True if user was deleted

@with_db_connection
def get_users_by_age_range(conn, min_age, max_age):
    """Get users within a specific age range."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE age BETWEEN ? AND ?",
        (min_age, max_age)
    )
    return cursor.fetchall()

# Enhanced version with configurable database path
def with_db_connection_configurable(db_path='users.db'):
    """
    Enhanced version that allows specifying the database path.
    Usage: @with_db_connection_configurable('custom.db')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            conn = None
            try:
                connection_logger.info(f"Opening database connection to {db_path}")
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                
                result = func(conn, *args, **kwargs)
                conn.commit()
                connection_logger.info("Database transaction committed successfully")
                return result
                
            except sqlite3.Error as e:
                connection_logger.error(f"Database error in {func.__name__}: {e}")
                if conn:
                    conn.rollback()
                raise e
                
            except Exception as e:
                connection_logger.error(f"Error in {func.__name__}: {e}")
                if conn:
                    conn.rollback()
                raise e
                
            finally:
                if conn:
                    conn.close()
                    connection_logger.info("Database connection closed")
        return wrapper
    return decorator

# Example using configurable decorator
@with_db_connection_configurable('test_users.db')
def get_user_count(conn):
    """Get total number of users."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    result = cursor.fetchone()
    return result['count'] if result else 0

# Setup function to create test database
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
        ('David Wilson', 'david@example.com', 41),
        ('Eve Martinez', 'eve@example.com', 29)
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)", 
        sample_users
    )
    
    conn.commit()
    conn.close()
    print("Test database created with sample data!")

# Testing the decorator
if __name__ == "__main__":
    # Setup test database
    setup_test_database()
    
    print("\n" + "="*60)
    print("TESTING DATABASE CONNECTION MANAGEMENT DECORATOR")
    print("="*60)
    
    # Test 1: Fetch user by ID with automatic connection handling 
    print("\n1. Testing get_user_by_id:")
    user = get_user_by_id(user_id=1)
    if user:
        print(f"User found: ID={user['id']}, Name={user['name']}, Email={user['email']}, Age={user['age']}")
    else:
        print("No user found with ID 1")
    
    # Test 2: Get all users
    print("\n2. Testing get_all_users:")
    all_users = get_all_users()
    print(f"Total users: {len(all_users)}")
    for user in all_users:
        print(f"  - {user['name']} ({user['email']}) - Age: {user['age']}")
    
    # Test 3: Create new user
    print("\n3. Testing create_user:")
    try:
        new_user_id = create_user("Frank Miller", "frank@example.com", 35)
        print(f"Created new user with ID: {new_user_id}")
    except sqlite3.IntegrityError:
        print("User with this email already exists")
    
    # Test 4: Update user email
    print("\n4. Testing update_user_email:")
    success = update_user_email(2, "bob.smith.updated@example.com")
    print(f"Email update {'successful' if success else 'failed'}")
    
    # Test 5: Get users by age range
    print("\n5. Testing get_users_by_age_range:")
    young_users = get_users_by_age_range(25, 30)
    print(f"Users aged 25-30: {len(young_users)}")
    for user in young_users:
        print(f"  - {user['name']} (Age: {user['age']})")
    
    # Test 6: Test error handling
    print("\n6. Testing error handling:")
    try:
        # This should fail because user ID 999 doesn't exist for update
        success = update_user_email(999, "nonexistent@example.com")
        print(f"Update result: {success}")
    except Exception as e:
        print(f"Handled error gracefully: {e}")
    
    # Test 7: Test configurable database path
    print("\n7. Testing configurable database decorator:")
    # First copy the database to test path
    import shutil
    shutil.copy('users.db', 'test_users.db')
    
    user_count = get_user_count()
    print(f"Total users in test database: {user_count}")
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
