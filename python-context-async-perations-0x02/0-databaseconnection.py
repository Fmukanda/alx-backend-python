import sqlite3
import logging
from typing import Optional, List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_context_manager')

class DatabaseConnection:
    """
    A context manager for handling database connections automatically.
    
    Args:
        db_path (str): Path to the SQLite database file
        timeout (float): Timeout for database operations in seconds
        row_factory: Factory for converting rows to objects (default: sqlite3.Row)
    """
    
    def __init__(self, db_path: str = 'users.db', timeout: float = 5.0, 
                 row_factory=sqlite3.Row):
        self.db_path = db_path
        self.timeout = timeout
        self.row_factory = row_factory
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
    
    def __enter__(self) -> 'DatabaseConnection':
        """Enter the runtime context and open the database connection."""
        try:
            logger.info(f"Opening database connection to {self.db_path}")
            self.connection = sqlite3.connect(
                self.db_path, 
                timeout=self.timeout
            )
            self.connection.row_factory = self.row_factory
            self.cursor = self.connection.cursor()
            logger.info("Database connection established successfully")
            return self
        except sqlite3.Error as e:
            logger.error(f"Failed to open database connection: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the runtime context and close the database connection."""
        try:
            if self.cursor:
                self.cursor.close()
                logger.debug("Database cursor closed")
            
            if self.connection:
                if exc_type is not None:
                    # An exception occurred, rollback any changes
                    self.connection.rollback()
                    logger.info("Transaction rolled back due to exception")
                else:
                    # No exception, commit any changes
                    self.connection.commit()
                    logger.debug("Transaction committed")
                
                self.connection.close()
                logger.info("Database connection closed")
            
            # Return False to propagate exceptions, True to suppress them
            return False
            
        except sqlite3.Error as e:
            logger.error(f"Error while closing database connection: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return the results."""
        if not self.cursor:
            raise RuntimeError("Database connection not established")
        
        try:
            logger.info(f"Executing query: {query}")
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            results = self.cursor.fetchall()
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return [dict(row) for row in results]
            
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an update/insert/delete query and return the number of affected rows."""
        if not self.cursor:
            raise RuntimeError("Database connection not established")
        
        try:
            logger.info(f"Executing update: {query}")
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            affected_rows = self.cursor.rowcount
            logger.info(f"Update executed successfully, affected {affected_rows} rows")
            return affected_rows
            
        except sqlite3.Error as e:
            logger.error(f"Update execution failed: {e}")
            raise
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names in the database."""
        if not self.cursor:
            raise RuntimeError("Database connection not established")
        
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in self.cursor.fetchall()]
            logger.info(f"Found {len(tables)} tables in database")
            return tables
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get table names: {e}")
            raise

# Enhanced version with transaction support
class DatabaseTransaction(DatabaseConnection):
    """
    Enhanced context manager with explicit transaction control.
    """
    
    def __init__(self, db_path: str = 'users.db', timeout: float = 5.0, 
                 row_factory=sqlite3.Row, autocommit: bool = True):
        super().__init__(db_path, timeout, row_factory)
        self.autocommit = autocommit
        self.in_transaction = False
    
    def __enter__(self) -> 'DatabaseTransaction':
        """Enter the context and start a transaction if autocommit is False."""
        super().__enter__()
        if not self.autocommit and self.connection:
            self.connection.execute("BEGIN TRANSACTION")
            self.in_transaction = True
            logger.info("Transaction started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the context and handle transaction commit/rollback."""
        try:
            if self.in_transaction and self.connection:
                if exc_type is None:
                    self.connection.commit()
                    logger.info("Transaction committed")
                else:
                    self.connection.rollback()
                    logger.info("Transaction rolled back due to exception")
            
            return super().__exit__(exc_type, exc_val, exc_tb)
            
        except sqlite3.Error as e:
            logger.error(f"Error during transaction handling: {e}")
            return False
    
    def commit(self) -> None:
        """Manually commit the current transaction."""
        if self.connection and self.in_transaction:
            self.connection.commit()
            self.in_transaction = False
            logger.info("Manual commit completed")
    
    def rollback(self) -> None:
        """Manually rollback the current transaction."""
        if self.connection and self.in_transaction:
            self.connection.rollback()
            self.in_transaction = False
            logger.info("Manual rollback completed")

# Helper function to setup test database
def setup_test_database(db_path: str = 'users.db'):
    """Create a test database with sample data."""
    with DatabaseConnection(db_path) as db:
        db.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        sample_users = [
            ('Alice Johnson', 'alice@example.com', 28),
            ('Bob Smith', 'bob@example.com', 32),
            ('Carol Davis', 'carol@example.com', 25),
            ('David Wilson', 'david@example.com', 35),
            ('Eva Martinez', 'eva@example.com', 29)
        ]
        
        for user in sample_users:
            try:
                db.cursor.execute(
                    "INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)",
                    user
                )
            except sqlite3.IntegrityError:
                pass  # User already exists
        
        db.connection.commit()
        print(f"Test database created at {db_path} with sample data!")

# Demonstration of using the context manager
def demonstrate_context_manager():
    """Demonstrate the usage of DatabaseConnection context manager."""
    
    # Setup test database first
    setup_test_database()
    
    print("=" * 70)
    print("DEMONSTRATING DATABASE CONTEXT MANAGER")
    print("=" * 70)
    
    # Example 1: Basic usage with SELECT query
    print("\n1. Basic SELECT query with context manager:")
    try:
        with DatabaseConnection() as db:
            results = db.execute_query("SELECT * FROM users")
            
            print(f"\nFound {len(results)} users:")
            for user in results:
                print(f"  - {user['name']} ({user['email']}), Age: {user['age']}")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Using the cursor directly
    print("\n2. Using cursor directly within context:")
    try:
        with DatabaseConnection() as db:
            db.cursor.execute("SELECT name, email FROM users WHERE age > ?", (28,))
            results = db.cursor.fetchall()
            
            print(f"\nUsers older than 28:")
            for row in results:
                print(f"  - {row['name']}: {row['email']}")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Transaction management
    print("\n3. Transaction management with DatabaseTransaction:")
    try:
        with DatabaseTransaction(autocommit=False) as db:
            # Insert a new user
            db.execute_update(
                "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
                ("Frank Miller", "frank@example.com", 40)
            )
            
            # Update an existing user
            db.execute_update(
                "UPDATE users SET age = ? WHERE name = ?",
                (33, "Bob Smith")
            )
            
            # Query to verify changes (within transaction)
            users = db.execute_query("SELECT name, age FROM users WHERE name IN (?, ?)", 
                                   ("Frank Miller", "Bob Smith"))
            
            print("\nChanges within transaction:")
            for user in users:
                print(f"  - {user['name']}: Age {user['age']}")
            
            # Commit the transaction
            db.commit()
            
    except Exception as e:
        print(f"Transaction error: {e}")
    
    # Example 4: Error handling with automatic rollback
    print("\n4. Error handling with automatic rollback:")
    try:
        with DatabaseTransaction(autocommit=False) as db:
            # This will cause an integrity error (duplicate email)
            db.execute_update(
                "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
                ("Test User", "alice@example.com", 99)  # Duplicate email
            )
            
    except sqlite3.IntegrityError as e:
        print(f"Expected integrity error: {e}")
    
    # Example 5: Get database metadata
    print("\n5. Database metadata:")
    try:
        with DatabaseConnection() as db:
            tables = db.get_table_names()
            print(f"Tables in database: {tables}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 6: Using with different database
    print("\n6. Using with different database file:")
    try:
        with DatabaseConnection(db_path=':memory:') as db:
            # Create a temporary table in memory database
            db.cursor.execute('''
                CREATE TABLE temp_data (
                    id INTEGER PRIMARY KEY,
                    value TEXT
                )
            ''')
            db.cursor.execute("INSERT INTO temp_data (value) VALUES ('test')")
            results = db.execute_query("SELECT * FROM temp_data")
            print(f"Memory database results: {results}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 70)
    print("CONTEXT MANAGER DEMONSTRATION COMPLETE")
    print("=" * 70)

# Main execution
if __name__ == "__main__":
    demonstrate_context_manager()

    # Using the context manager with SELECT * FROM users
with DatabaseConnection() as db:
    results = db.execute_query("SELECT * FROM users")
    for user in results:
        print(f"User: {user['name']}, Email: {user['email']}, Age: {user['age']}")
    
