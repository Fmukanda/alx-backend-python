import seed as sd
import mysql.connector
from mysql.connector import errorcode

# SELECT * FROM user_data LIMIT
# paginate_users(page_size, offset)

def paginate_users(connection, page_size, offset):
    """
    Fetches a single page of users from the database.

    """
    if connection is None:
        return []

    cursor = connection.cursor(buffered=True)
    try:
        query = f"SELECT user_id, name, email, age FROM {sd.TABLE_NAME} LIMIT %s OFFSET %s"
        cursor.execute(query, (page_size, offset))
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error fetching data: {err}")
        return []
    finally:
        cursor.close()

def lazy_paginate(connection, page_size):
    """
    A generator function to fetch and process data in batches (pages) from the users database.
    It fetches a new page only when needed.

    """
    offset = 0
    while True:
        page = paginate_users(connection, page_size, offset)
        if not page:
            break
        yield page
        offset += page_size

if __name__ == '__main__':

    connection_db = sd.connect_to_prodev()

    if connection_db:
        try:
            PAGE_SIZE = 50
            print(f"\nLazily fetching users in pages of {PAGE_SIZE}...")
            
            for page_number, page in enumerate(lazy_paginate(connection_db, PAGE_SIZE)):
                print(f"\n--- Processing Page {page_number + 1} ---")                
                for user in page:
                    user_id, name, email, age = user
                    print(f"User ID: {user_id}, Name: {name}, Email: {email}, Age: {age}")
                
        finally:
            connection_db.close()
            print("\nDatabase connection closed.")

