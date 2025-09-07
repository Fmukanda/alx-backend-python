import seed as sd
import mysql.connector
from mysql.connector import errorcode

def stream_users(connection):
    """
    A generator function that fetches all rows from the user_data table
    one by one and yields them.

    """
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        query = f"SELECT user_id, name, email, age FROM {sd.TABLE_NAME}"
        cursor.execute(query)

        for row in cursor:
            yield row
    except mysql.connector.Error as err:
        print(f"Error fetching data: {err}")
    finally:      
        cursor.close()


if __name__ == '__main__':
    connection_db = sd.connect_to_prodev()

    if connection_db:
        try:
            print("\nStreaming users from the database:")
            user_generator = stream_users(connection_db)
            
            for user in user_generator:
                user_id, name, email, age = user
                print(f"User ID: {user_id}, Name: {name}, Email: {email}, Age: {age}")
                
        finally:          
            connection_db.close()
            print("\nDatabase connection closed.")

