import sqlite3 
import functools
import logging

# Set up logging for transaction management
logging.basicConfig(level=logging.INFO)
connection_logger = logging.getLogger('db_connections')
transaction_logger = logging.getLogger('db_transactions')

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
            # Handle any exceptions - let transactional decorator handle commit/rollback
            connection_logger.error(f"Error in {func.__name__}: {e}")
            raise e
            
        finally:
            # Always close the connection
            if conn:
                conn.close()
                connection_logger.info("Database connection closed")
    
    return wrapper

def transactional(func):
    """
    Decorator that manages database transactions by automatically committing 
    or rolling back changes. If the function raises an error, rollback; 
    otherwise commit the transaction.
    
    This decorator expects the connection to be the first parameter of the function.
    """
    @functools.wraps(func)
    def wrapper(conn, *args, **kwargs):
        # Begin transaction (SQLite uses autocommit=False by default when using execute)
        transaction_logger.info(f"Starting transaction for {func.__name__}")
        
        try:
            # Execute the function
            result = func(conn, *args, **kwargs)
            
            # If we get here, the function succeeded - commit the transaction
            conn.commit()
            transaction_logger.info(f"Transaction committed successfully for {func.__name__}")
            
            return result
            
        except Exception as e:
            # Function raised an exception - rollback the transaction
            conn.rollback()
            transaction_logger.error(f"Transaction rolled back for {func.__name__} due to error: {e}")
            
            # Re-raise the exception so calling code can handle it
            raise e
    
    return wrapper

@with_db_connection 
@transactional 
def update_user_email(conn, user_id, new_email): 
    cursor = conn.cursor() 
    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
    
    # Check if any rows were affected
    if cursor.rowcount == 0:
        raise ValueError(f"No user found with ID {user_id}")
    
    transaction_logger.info(f"Updated email for user {user_id} to {new_email}")

# Additional example functions using both decorators

@with_db_connection
@transactional
def create_user_with_validation(conn, name, email, age):
    """Create a user with validation - demonstrates transaction rollback on error."""
    cursor = conn.cursor()
    
    # Validate age
    if age < 0 or age > 150:
        raise ValueError("Age must be between 0 and 150")
    
    # Validate email format (simple check)
    if '@' not in email or '.' not in email:
        raise ValueError("Invalid email format")
    
    # Insert the user
    cursor.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        (name, email, age)
    )
    
    user_id = cursor.lastrowid
    transaction_logger.info(f"Created user {name} with ID {user_id}")
    
    return user_id

@with_db_connection
@transactional
def transfer_credits_between_users(conn, from_user_id, to_user_id, amount):
    """
    Transfer credits between users - demonstrates complex transaction.
    Both operations must succeed or both must fail.
    """
    cursor = conn.cursor()
    
    # Validate amount
    if amount <= 0:
        raise ValueError("Transfer amount must be positive")
    
    # Check if sender has enough credits
    cursor.execute("SELECT credits FROM users WHERE id = ?", (from_user_id,))
    sender = cursor.fetchone()
    if not sender:
        raise ValueError(f"Sender user {from_user_id} not found")
    
    if sender['credits'] < amount:
        raise ValueError(f"Insufficient credits. Available: {sender['credits']}, Required: {amount}")
    
    # Check if receiver exists
    cursor.execute("SELECT id FROM users WHERE id = ?", (to_user_id,))
    receiver = cursor.fetchone()
    if not receiver:
        raise ValueError(f"Receiver user {to_user_id} not found")
    
    # Perform the transfer
    # Deduct from sender
    cursor.execute(
        "UPDATE users SET credits = credits - ? WHERE id = ?",
        (amount, from_user_id)
    )
    
    # Add to receiver
    cursor.execute(
        "UPDATE users SET credits = credits + ? WHERE id = ?",
        (amount, to_user_id)
    )
    
    transaction_logger.info(f"Transferred {amount} credits from user {from_user_id} to user {to_user_id}")

@with_db_connection
@transactional
def bulk_update_ages(conn, age_updates):
    """
    Update multiple users' ages in a single transaction.
    age_updates should be a list of tuples: [(user_id, new_age), ...]
    """
    cursor = conn.cursor()
    
    updated_count = 0
    for user_id, new_age in age_updates:
        if new_age < 0 or new_age > 150:
            raise ValueError(f"Invalid age {new_age} for user {user_id}")
        
        cursor.execute("UPDATE users SET age = ? WHERE id = ?", (new_age, user_id))
        if cursor.rowcount > 0:
            updated_count += 1
    
    transaction_logger.info(f"Bulk updated ages for {updated_count} users")
    return updated_count

# Helper function to setup test database with credits column
def setup_test_database():
    """Create a test database with sample data including credits."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Create users table with credits column
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
    print("Test database created with sample data and credits!")

@with_db_connection
def get_user_by_id(conn, user_id):
    """Helper function to get user details."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

@with_db_connection
def get_all_users(conn):
    """Helper function to get all users."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Testing the decorators
if __name__ == "__main__":
    # Setup test database
    setup_test_database()
    
    print("\n" + "="*70)
    print("TESTING TRANSACTIONAL DATABASE DECORATOR")
    print("="*70)
    
    # Test 1: Update user's email with automatic transaction handling 
    print("\n1. Testing successful email update:")
    try:
        update_user_email(user_id=1, new_email='crawford_cartwright@hotmail.com')
        print("Email update completed successfully")
        
        # Verify the update
        user = get_user_by_id(user_id=1)
        print(f"Updated user: {user['name']} - {user['email']}")
        
    except Exception as e:
        print(f"Email update failed: {e}")
    
    # Test 2: Test transaction rollback with invalid user ID
    print("\n2. Testing transaction rollback (invalid user ID):")
    try:
        update_user_email(user_id=999, new_email='nonexistent@example.com')
        print("This should not print - update should fail")
    except Exception as e:
        print(f"Expected error caught: {e}")
        print("Transaction was properly rolled back")
    
    # Test 3: Create user with validation
    print("\n3. Testing user creation with validation:")
    try:
        # This should succeed
        new_user_id = create_user_with_validation("Frank Miller", "frank@example.com", 35)
        print(f"Successfully created user with ID: {new_user_id}")
        
        # This should fail due to invalid age
        create_user_with_validation("Invalid User", "invalid@example.com", -5)
        
    except Exception as e:
        print(f"Expected validation error: {e}")
        print("Transaction was properly rolled back")
    
    # Test 4: Credit transfer transaction
    print("\n4. Testing credit transfer:")
    print("Before transfer:")
    user1 = get_user_by_id(user_id=1)
    user2 = get_user_by_id(user_id=2)
    print(f"  User 1 credits: {user1['credits']}")
    print(f"  User 2 credits: {user2['credits']}")
    
    try:
        transfer_credits_between_users(from_user_id=1, to_user_id=2, amount=50.0)
        print("Credit transfer completed successfully")
        
        print("After transfer:")
        user1 = get_user_by_id(user_id=1)
        user2 = get_user_by_id(user_id=2)
        print(f"  User 1 credits: {user1['credits']}")
        print(f"  User 2 credits: {user2['credits']}")
        
    except Exception as e:
        print(f"Credit transfer failed: {e}")
    
    # Test 5: Failed credit transfer (insufficient funds)
    print("\n5. Testing failed credit transfer (insufficient funds):")
    try:
        transfer_credits_between_users(from_user_id=3, to_user_id=1, amount=1000.0)
        print("This should not print - transfer should fail")
    except Exception as e:
        print(f"Expected error: {e}")
        print("Transaction was properly rolled back - no credits were transferred")
    
    # Test 6: Bulk update with rollback on error
    print("\n6. Testing bulk update with rollback:")
    age_updates = [
        (1, 30),  # Valid
        (2, 35),  # Valid  
        (3, -10)  # Invalid - should cause rollback
    ]
    
    print("Original ages:")
    for user_id in [1, 2, 3]:
        user = get_user_by_id(user_id=user_id)
        print(f"  User {user_id}: {user['age']} years old")
    
    try:
        bulk_update_ages(age_updates)
        print("Bulk update completed")
    except Exception as e:
        print(f"Bulk update failed: {e}")
        print("All updates were rolled back")
        
    print("Ages after failed bulk update (should be unchanged):")
    for user_id in [1, 2, 3]:
        user = get_user_by_id(user_id=user_id)
        print(f"  User {user_id}: {user['age']} years old")
    
    print("\n" + "="*70)
    print("TRANSACTIONAL DECORATOR TESTING COMPLETE")
    print("="*70)
