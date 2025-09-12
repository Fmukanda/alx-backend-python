import asyncio
import aiosqlite
import logging
from typing import List, Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('async_db')

# Database configuration
DB_PATH = 'users.db'

async def setup_database():
    """Create and populate the test database with sample data."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Enable row factory for dictionary-like access
            db.row_factory = aiosqlite.Row
            
            # Create users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    age INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert sample data
            sample_users = [
                ('Alice Johnson', 'alice@example.com', 28),
                ('Bob Smith', 'bob@example.com', 45),
                ('Carol Davis', 'carol@example.com', 32),
                ('David Wilson', 'david@example.com', 52),
                ('Eva Martinez', 'eva@example.com', 29),
                ('Frank Miller', 'frank@example.com', 38),
                ('Grace Lee', 'grace@example.com', 61),
                ('Henry Brown', 'henry@example.com', 42),
                ('Ivy Taylor', 'ivy@example.com', 27),
                ('Jack Anderson', 'jack@example.com', 48)
            ]
            
            for user in sample_users:
                try:
                    await db.execute(
                        "INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)",
                        user
                    )
                except Exception as e:
                    logger.warning(f"Could not insert user {user[0]}: {e}")
            
            await db.commit()
            logger.info("Database setup completed with sample data")
            
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise

async def async_fetch_users() -> List[Dict[str, Any]]:
    """
    Asynchronously fetch all users from the database.
    
    Returns:
        List of dictionaries containing user data
    """
    logger.info("Starting to fetch all users...")
    start_time = datetime.now()
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY name") as cursor:
                rows = await cursor.fetchall()
                results = [dict(row) for row in rows]
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Fetched {len(results)} users in {execution_time:.3f} seconds")
                
                return results
                
    except Exception as e:
        logger.error(f"Error fetching all users: {e}")
        raise

async def async_fetch_older_users(age_threshold: int = 40) -> List[Dict[str, Any]]:
    """
    Asynchronously fetch users older than the specified age threshold.
    
    Args:
        age_threshold: Minimum age to filter users (default: 40)
    
    Returns:
        List of dictionaries containing user data for older users
    """
    logger.info(f"Starting to fetch users older than {age_threshold}...")
    start_time = datetime.now()
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE age > ? ORDER BY age DESC",
                (age_threshold,)
            ) as cursor:
                rows = await cursor.fetchall()
                results = [dict(row) for row in rows]
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Fetched {len(results)} older users in {execution_time:.3f} seconds")
                
                return results
                
    except Exception as e:
        logger.error(f"Error fetching older users: {e}")
        raise

async def async_fetch_user_count() -> int:
    """Asynchronously fetch the total count of users."""
    logger.info("Starting to fetch user count...")
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) as count FROM users") as cursor:
                row = await cursor.fetchone()
                count = row['count'] if row else 0
                logger.info(f"Total user count: {count}")
                return count
                
    except Exception as e:
        logger.error(f"Error fetching user count: {e}")
        raise

async def async_fetch_young_users(age_threshold: int = 30) -> List[Dict[str, Any]]:
    """
    Asynchronously fetch users younger than or equal to the specified age.
    
    Args:
        age_threshold: Maximum age to filter users (default: 30)
    
    Returns:
        List of dictionaries containing user data for young users
    """
    logger.info(f"Starting to fetch users younger than or equal to {age_threshold}...")
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE age <= ? ORDER BY age ASC",
                (age_threshold,)
            ) as cursor:
                rows = await cursor.fetchall()
                results = [dict(row) for row in rows]
                logger.info(f"Fetched {len(results)} young users")
                return results
                
    except Exception as e:
        logger.error(f"Error fetching young users: {e}")
        raise

async def fetch_concurrently():
    """
    Execute multiple database queries concurrently using asyncio.gather.
    
    Returns:
        Tuple containing results from all concurrent queries
    """
    logger.info("Starting concurrent database queries...")
    start_time = datetime.now()
    
    try:
        # Execute all queries concurrently
        results = await asyncio.gather(
            async_fetch_users(),           # Fetch all users
            async_fetch_older_users(40),   # Fetch users older than 40
            async_fetch_user_count(),      # Fetch total user count
            async_fetch_young_users(30),   # Fetch users 30 or younger
            return_exceptions=False        # Raise exceptions immediately
        )
        
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"All concurrent queries completed in {total_time:.3f} seconds")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in concurrent queries: {e}")
        raise

async def fetch_sequentially():
    """
    Execute the same queries sequentially for comparison.
    """
    logger.info("Starting sequential database queries...")
    start_time = datetime.now()
    
    try:
        # Execute queries one after another
        all_users = await async_fetch_users()
        older_users = await async_fetch_older_users(40)
        user_count = await async_fetch_user_count()
        young_users = await async_fetch_young_users(30)
        
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"All sequential queries completed in {total_time:.3f} seconds")
        
        return all_users, older_users, user_count, young_users
        
    except Exception as e:
        logger.error(f"Error in sequential queries: {e}")
        raise

async def demonstrate_concurrent_vs_sequential():
    """Demonstrate the difference between concurrent and sequential execution."""
    print("=" * 70)
    print("CONCURRENT VS SEQUENTIAL DATABASE QUERIES")
    print("=" * 70)
    
    # First, run concurrent queries
    print("\n1. Running concurrent queries with asyncio.gather():")
    concurrent_start = datetime.now()
    try:
        concurrent_results = await fetch_concurrently()
        concurrent_time = (datetime.now() - concurrent_start).total_seconds()
        
        all_users, older_users, user_count, young_users = concurrent_results
        
        print(f"\nConcurrent results:")
        print(f"  - Total users: {user_count}")
        print(f"  - Users older than 40: {len(older_users)}")
        print(f"  - Users 30 or younger: {len(young_users)}")
        print(f"  - Concurrent execution time: {concurrent_time:.3f} seconds")
        
        # Show some sample data
        print(f"\nSample older users:")
        for user in older_users[:2]:
            print(f"  - {user['name']} (Age: {user['age']})")
            
    except Exception as e:
        print(f"Error in concurrent execution: {e}")
        return
    
    # Then, run sequential queries for comparison
    print("\n2. Running sequential queries:")
    sequential_start = datetime.now()
    try:
        sequential_results = await fetch_sequentially()
        sequential_time = (datetime.now() - sequential_start).total_seconds()
        
        print(f"  - Sequential execution time: {sequential_time:.3f} seconds")
        print(f"  - Time saved: {sequential_time - concurrent_time:.3f} seconds")
        print(f"  - Performance improvement: {((sequential_time - concurrent_time) / sequential_time * 100):.1f}%")
        
    except Exception as e:
        print(f"Error in sequential execution: {e}")
        return
    
    # Demonstrate individual query timing
    print("\n3. Individual query timing demonstration:")
    try:
        # Run each query individually to see their individual times
        individual_times = {}
        
        start = datetime.now()
        await async_fetch_users()
        individual_times['all_users'] = (datetime.now() - start).total_seconds()
        
        start = datetime.now()
        await async_fetch_older_users(40)
        individual_times['older_users'] = (datetime.now() - start).total_seconds()
        
        start = datetime.now()
        await async_fetch_user_count()
        individual_times['user_count'] = (datetime.now() - start).total_seconds()
        
        start = datetime.now()
        await async_fetch_young_users(30)
        individual_times['young_users'] = (datetime.now() - start).total_seconds()
        
        total_individual_time = sum(individual_times.values())
        print(f"  - Sum of individual query times: {total_individual_time:.3f} seconds")
        print(f"  - Concurrent execution time: {concurrent_time:.3f} seconds")
        print(f"  - Efficiency gain: {total_individual_time - concurrent_time:.3f} seconds")
        
    except Exception as e:
        print(f"Error in individual timing: {e}")

async def main():
    """Main function to run the demonstration."""
    print("Setting up database...")
    await setup_database()
    
    await demonstrate_concurrent_vs_sequential()
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
