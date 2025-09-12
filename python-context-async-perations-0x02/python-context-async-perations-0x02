import sqlite3
import logging
from typing import Optional, List, Dict, Any, Union, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('query_executor')

class ExecuteQuery:
    """
    A reusable context manager that executes a SQL query and manages the database connection.
    
    Args:
        query (str): The SQL query to execute
        params (Union[tuple, dict, None]): Parameters for the query
        db_path (str): Path to the SQLite database file
        timeout (float): Timeout for database operations in seconds
        fetch_all (bool): Whether to fetch all results or just one
    """
    
    def __init__(self, query: str, params: Optional[Union[tuple, dict, list]] = None, 
                 db_path: str = 'users.db', timeout: float = 5.0, fetch_all: bool = True):
        self.query = query
        self.params = params
        self.db_path = db_path
        self.timeout = timeout
        self.fetch_all = fetch_all
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.results: Optional[List[Dict[str, Any]]] = None
    
    def __enter__(self) -> List[Dict[str, Any]]:
        """Enter the runtime context, execute the query, and return results."""
        try:
            # Open database connection
            logger.info(f"Opening database connection to {self.db_path}")
            self.connection = sqlite3.connect(self.db_path, timeout=self.timeout)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            
            # Execute the query
            logger.info(f"Executing query: {self.query}")
            if self.params:
                logger.info(f"With parameters: {self.params}")
                self.cursor.execute(self.query, self.params)
            else:
                self.cursor.execute(self.query)
            
            # Fetch results
            if self.fetch_all:
                raw_results = self.cursor.fetchall()
            else:
                raw_result = self.cursor.fetchone()
                raw_results = [raw_result] if raw_result else []
            
            # Convert to list of dictionaries
            self.results = [dict(row) for row in raw_results]
            
            logger.info(f"Query executed successfully, returned {len(self.results)} rows")
            return self.results
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            self._close_connection()
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self._close_connection()
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the runtime context and close the database connection."""
        try:
            self._close_connection()
            # Return False to propagate exceptions, True to suppress them
            return False
        except Exception as e:
            logger.error(f"Error while closing connection: {e}")
            return False
    
    def _close_connection(self) -> None:
        """Close the database connection if it's open."""
        if self.cursor:
            try:
                self.cursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor: {e}")
        
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

# Enhanced version with transaction support and more features
class ExecuteQueryAdvanced(ExecuteQuery):
    """
    Enhanced version with transaction support, batch operations, and more features.
    """
    
    def __init__(self, query: str, params: Optional[Union[tuple, dict, list]] = None,
                 db_path: str = 'users.db', timeout: float = 5.0, fetch_all: bool = True,
                 autocommit: bool = True, return_cursor: bool = False):
        super().__init__(query, params, db_path, timeout, fetch_all)
        self.autocommit = autocommit
        self.return_cursor = return_cursor
        self.in_transaction = False
    
    def __enter__(self) -> Union[List[Dict[str, Any]], sqlite3.Cursor]:
        """Enter the context, execute query, and return results or cursor."""
        try:
            # Open connection
            self.connection = sqlite3.connect(self.db_path, timeout=self.timeout)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            
            # Start transaction if not autocommit
            if not self.autocommit:
                self.cursor.execute("BEGIN TRANSACTION")
                self.in_transaction = True
                logger.info("Transaction started")
            
            # Execute query
            logger.info(f"Executing: {self.query}")
            if self.params:
                logger.info(f"With params: {self.params}")
                self.cursor.execute(self.query, self.params)
            else:
                self.cursor.execute(self.query)
            
            # Return cursor if requested, otherwise fetch results
            if self.return_cursor:
                return self.cursor
            
            # Fetch results
            if self.fetch_all:
                raw_results = self.cursor.fetchall()
            else:
                raw_result = self.cursor.fetchone()
                raw_results = [raw_result] if raw_result else []
            
            self.results = [dict(row) for row in raw_results]
            logger.info(f"Returning {len(self.results)} results")
            return self.results
            
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            self._rollback_if_needed()
            self._close_connection()
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the context, handling transactions and closing connection."""
        try:
            if self.in_transaction:
                if exc_type is None:
                    self.connection.commit()
                    logger.info("Transaction committed")
                else:
                    self.connection.rollback()
                    logger.info("Transaction rolled back due to exception")
            
            self._close_connection()
            return False
            
        except Exception as e:
            logger.error(f"Error in context exit: {e}")
            return False
    
    def _rollback_if_needed(self) -> None:
        """Rollback transaction if needed."""
        if self.in_transaction and self.connection:
            try:
                self.connection.rollback()
                logger.info("Transaction rolled back due to error")
            except Exception as e:
                logger.warning(f"Error during rollback: {e}")

# Factory function for easy creation
def execute_query(query: str, params: Optional[Union[tuple, dict, list]] = None, 
                 db_path: str = 'users.db', **kwargs) -> List[Dict[str, Any]]:
    """
    Factory function to easily execute a query using the context manager.
    
    Example:
        results = execute_query("SELECT * FROM users WHERE age > ?", (25,))
    """
    with ExecuteQuery(query, params, db_path, **kwargs) as results:
        return results

# Helper function to setup test database
def setup_test_database(db_path: str = 'users.db'):
    """Create a test database with sample data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
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
        ('Eva Martinez', 'eva@example.com', 29),
        ('Frank Miller', 'frank@example.com', 22),
        ('Grace Lee', 'grace@example.com', 40)
    ]
    
    for user in sample_users:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)",
                user
            )
        except sqlite3.IntegrityError:
            pass  # User already exists
    
    conn.commit()
    conn.close()
    print(f"Test database created at {db_path} with {len(sample_users)} users!")

# Demonstration of the ExecuteQuery context manager
def demonstrate_execute_query():
    """Demonstrate the usage of ExecuteQuery context manager."""
    
    # Setup test database first
    setup_test_database()
    
    print("=" * 70)
    print("DEMONSTRATING EXECUTEQUERY CONTEXT MANAGER")
    print("=" * 70)
    
    # Example 1: Basic usage with the specified query
    print("\n1. Basic usage with SELECT * FROM users WHERE age > ? and parameter 25:")
    try:
        with ExecuteQuery(
            query="SELECT * FROM users WHERE age > ?", 
            params=(25,)
        ) as results:
            
            print(f"\nFound {len(results)} users older than 25:")
            for user in results:
                print(f"  - {user['name']} (Age: {user['age']}, Email: {user['email']})")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Using different parameters
    print("\n2. Using different age threshold (30):")
    try:
        with ExecuteQuery(
            query="SELECT * FROM users WHERE age > ?", 
            params=(30,)
        ) as results:
            
            print(f"\nFound {len(results)} users older than 30:")
            for user in results:
                print(f"  - {user['name']} (Age: {user['age']})")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Query without parameters
    print("\n3. Query without parameters (get all users):")
    try:
        with ExecuteQuery("SELECT * FROM users") as results:
            print(f"\nTotal users: {len(results)}")
            age_groups = {}
            for user in results:
                age_group = (user['age'] // 10) * 10
                age_groups[age_group] = age_groups.get(age_group, 0) + 1
            
            for age_group, count in sorted(age_groups.items()):
                print(f"  - Age {age_group}-{age_group+9}: {count} users")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: Using the factory function
    print("\n4. Using the factory function for convenience:")
    try:
        results = execute_query(
            "SELECT name, email FROM users WHERE age BETWEEN ? AND ?",
            params=(25, 35)
        )
        
        print(f"\nUsers between 25 and 35 years old:")
        for user in results:
            print(f"  - {user['name']}: {user['email']}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 5: Advanced version with transaction
    print("\n5. Using advanced version with transaction support:")
    try:
        with ExecuteQueryAdvanced(
            query="SELECT * FROM users WHERE age > ?",
            params=(25,),
            autocommit=False,
            fetch_all=True
        ) as results:
            
            print(f"\nTransaction mode - found {len(results)} users:")
            for user in results[:3]:  # Show first 3
                print(f"  - {user['name']} (Age: {user['age']})")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 6: Error handling demonstration
    print("\n6. Error handling with invalid query:")
    try:
        with ExecuteQuery("SELECT * FROM non_existent_table") as results:
            print("This should not be reached")
            
    except sqlite3.Error as e:
        print(f"Expected error handled gracefully: {e}")
    
    print("\n" + "=" * 70)
    print("EXECUTEQUERY DEMONSTRATION COMPLETE")
    print("=" * 70)

# Main execution
if __name__ == "__main__":
    demonstrate_execute_query()

   # Using the context manager with the specified query and parameter
with ExecuteQuery(
    query="SELECT * FROM users WHERE age > ?", 
    params=(25,)
) as results:
    for user in results:
        print(f"User: {user['name']}, Age: {user['age']}")
