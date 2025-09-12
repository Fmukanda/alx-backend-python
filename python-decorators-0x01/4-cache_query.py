import time
import sqlite3 
import functools
import hashlib
import json
from datetime import datetime, timedelta

# Global query cache with expiration support
query_cache = {}

def cache_query(max_age_seconds=300, max_size=1000, ignore_whitespace=True):
    """
    Decorator that caches the results of database queries to avoid redundant calls.
    
    Args:
        max_age_seconds (int): Maximum age of cached results in seconds (default: 300 = 5 minutes)
        max_size (int): Maximum number of items to keep in cache (default: 1000)
        ignore_whitespace (bool): Whether to ignore whitespace differences in queries (default: True)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract query from arguments
            query = None
            
            # Look for query in kwargs
            if 'query' in kwargs:
                query = kwargs['query']
            # Look for query as first positional argument
            elif len(args) > 0 and isinstance(args[0], str):
                query = args[0]
            
            if not query:
                # If no query found, execute without caching
                return func(*args, **kwargs)
            
            # Normalize query for caching (remove extra whitespace)
            if ignore_whitespace:
                normalized_query = ' '.join(query.split())
            else:
                normalized_query = query
            
            # Create cache key using hash of normalized query
            cache_key = hashlib.md5(normalized_query.encode('utf-8')).hexdigest()
            
            current_time = time.time()
            
            # Check if result is in cache and not expired
            if cache_key in query_cache:
                cached_data = query_cache[cache_key]
                
                # Check if cache entry is still valid
                if current_time - cached_data['timestamp'] <= max_age_seconds:
                    print(f"Using cached result for query: {normalized_query[:100]}...")
                    return cached_data['result']
                else:
                    # Remove expired entry
                    del query_cache[cache_key]
                    print(f"Cache expired for query: {normalized_query[:100]}...")
            
            # Execute the query and cache the result
            result = func(*args, **kwargs)
            
            # Clean up cache if it exceeds max size
            if len(query_cache) >= max_size:
                # Remove oldest entries (based on timestamp)
                oldest_keys = sorted(
                    query_cache.keys(),
                    key=lambda k: query_cache[k]['timestamp']
                )[:max_size // 4]  # Remove top 25% oldest
                
                for key in oldest_keys:
                    del query_cache[key]
            
            # Store result in cache
            query_cache[cache_key] = {
                'result': result,
                'timestamp': current_time,
                'query': normalized_query,
                'expires_at': current_time + max_age_seconds
            }
            
            print(f"Cached result for query: {normalized_query[:100]}...")
            return result
        
        return wrapper
    return decorator

# Advanced version with parameter support and cache statistics
def cache_query_advanced(max_age_seconds=300, max_size=1000, include_params=True):
    """
    Advanced cache decorator that supports query parameters and provides statistics.
    """
    cache_stats = {
        'hits': 0,
        'misses': 0,
        'expired': 0,
        'size': 0
    }
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal cache_stats
            
            # Extract query and parameters
            query = None
            params = None
            
            # Look for query in kwargs or args
            if 'query' in kwargs:
                query = kwargs['query']
            elif len(args) > 0 and isinstance(args[0], str):
                query = args[0]
                if len(args) > 1 and isinstance(args[1], (list, tuple, dict)):
                    params = args[1]
            
            if not query:
                return func(*args, **kwargs)
            
            # Normalize query
            normalized_query = ' '.join(query.split())
            
            # Create cache key including parameters if specified
            if include_params and params:
                key_data = normalized_query + json.dumps(params, sort_keys=True)
            else:
                key_data = normalized_query
            
            cache_key = hashlib.sha256(key_data.encode('utf-8')).hexdigest()
            current_time = time.time()
            
            # Check cache
            if cache_key in query_cache:
                cached_data = query_cache[cache_key]
                
                if current_time - cached_data['timestamp'] <= max_age_seconds:
                    cache_stats['hits'] += 1
                    print(f"Cache HIT for query: {normalized_query[:80]}...")
                    return cached_data['result']
                else:
                    cache_stats['expired'] += 1
                    del query_cache[cache_key]
            
            # Cache miss - execute query
            cache_stats['misses'] += 1
            result = func(*args, **kwargs)
            
            # Manage cache size
            if len(query_cache) >= max_size:
                # Remove least recently used entries
                lru_keys = sorted(
                    query_cache.keys(),
                    key=lambda k: query_cache[k]['timestamp']
                )[:max_size // 4]
                
                for key in lru_keys:
                    del query_cache[key]
            
            # Cache the result
            query_cache[cache_key] = {
                'result': result,
                'timestamp': current_time,
                'query': normalized_query,
                'params': params if include_params else None
            }
            
            cache_stats['size'] = len(query_cache)
            print(f"Cache MISS - stored: {normalized_query[:80]}...")
            
            return result
        
        # Add cache management methods to the wrapper
        def clear_cache():
            """Clear the query cache."""
            query_cache.clear()
            cache_stats.update({'hits': 0, 'misses': 0, 'expired': 0, 'size': 0})
            print("Query cache cleared")
        
        def get_cache_stats():
            """Get cache statistics."""
            return cache_stats.copy()
        
        def get_cache_info():
            """Get detailed cache information."""
            return {
                'total_entries': len(query_cache),
                'cache_stats': cache_stats,
                'oldest_entry': min((data['timestamp'] for data in query_cache.values()), default=None),
                'newest_entry': max((data['timestamp'] for data in query_cache.values()), default=None)
            }
        
        # Attach cache management methods to the wrapper function
        wrapper.clear_cache = clear_cache
        wrapper.get_cache_stats = get_cache_stats
        wrapper.get_cache_info = get_cache_info
        
        return wrapper
    return decorator

# Example usage with the existing with_db_connection decorator
def with_db_connection(func):
    """Decorator that handles database connections."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row
        try:
            result = func(conn, *args, **kwargs)
            return result
        finally:
            conn.close()
    return wrapper

@with_db_connection
@cache_query(max_age_seconds=60, max_size=100)  # Cache for 1 minute, max 100 items
def fetch_users_with_cache(conn, query):
    """Fetch users with query caching."""
    print(f"Executing database query: {query}")
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

@with_db_connection
@cache_query_advanced(max_age_seconds=120, include_params=True)
def fetch_users_with_params(conn, query, params=None):
    """Fetch users with parameterized queries and advanced caching."""
    print(f"Executing parameterized query: {query} with params: {params}")
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    return cursor.fetchall()

# Helper function to setup test database
def setup_test_database():
    """Create a test database with sample data."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER
        )
    ''')
    
    sample_users = [
        ('Alice Johnson', 'alice@example.com', 28),
        ('Bob Smith', 'bob@example.com', 32),
        ('Carol Davis', 'carol@example.com', 25)
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO users (name, email, age) VALUES (?, ?, ?)", 
        sample_users
    )
    
    conn.commit()
    conn.close()
    print("Test database created with sample data!")

# Demonstration
if __name__ == "__main__":
    setup_test_database()
    
    print("=" * 70)
    print("DEMONSTRATING QUERY CACHING")
    print("=" * 70)
    
    # First call - will execute and cache
    print("\n1. First call (will cache):")
    users1 = fetch_users_with_cache(query="SELECT * FROM users")
    print(f"Fetched {len(users1)} users")
    
    # Second call - should use cache
    print("\n2. Second call (should use cache):")
    users2 = fetch_users_with_cache(query="SELECT * FROM users")
    print(f"Fetched {len(users2)} users (from cache)")
    
    # Different query - will execute
    print("\n3. Different query (will execute):")
    users3 = fetch_users_with_cache(query="SELECT * FROM users WHERE age > 25")
    print(f"Fetched {len(users3)} users")
    
    # Same query again - should use cache
    print("\n4. Same query again (should use cache):")
    users4 = fetch_users_with_cache(query="SELECT * FROM users WHERE age > 25")
    print(f"Fetched {len(users4)} users (from cache)")
    
    # Test parameterized queries with advanced caching
    print("\n5. Parameterized query caching:")
    users5 = fetch_users_with_params(
        query="SELECT * FROM users WHERE age > ?", 
        params=(25,)
    )
    print(f"Fetched {len(users5)} users with age > 25")
    
    # Same parameterized query - should use cache
    users6 = fetch_users_with_params(
        query="SELECT * FROM users WHERE age > ?", 
        params=(25,)
    )
    print(f"Fetched {len(users6)} users with age > 25 (from cache)")
    
    # Different parameters - will execute
    users7 = fetch_users_with_params(
        query="SELECT * FROM users WHERE age > ?", 
        params=(30,)
    )
    print(f"Fetched {len(users7)} users with age > 30")
    
    # Show cache statistics
    print("\n6. Cache statistics:")
    stats = fetch_users_with_params.get_cache_stats()
    print(f"Hits: {stats['hits']}, Misses: {stats['misses']}, Expired: {stats['expired']}")
    
    # Clear cache and test again
    print("\n7. Clearing cache and testing again:")
    fetch_users_with_params.clear_cache()
    
    users8 = fetch_users_with_params(
        query="SELECT * FROM users WHERE age > ?", 
        params=(25,)
    )
    print(f"Fetched {len(users8)} users (after cache clear)")
    
    print("\n" + "=" * 70)
    print("CACHING DEMONSTRATION COMPLETE")
    print("=" * 70)
