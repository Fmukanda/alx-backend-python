import seed as sd
import mysql.connector
from mysql.connector import errorcode


def stream_users_in_batches(connection, batch_size):
    """
    A generator function that fetches all rows from the user_data table
    in batches and yields each batch.

    """
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        query = f"SELECT user_id, name, email, age FROM {sd.TABLE_NAME}"
        cursor.execute(query)

        while True:         
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield batch
    except mysql.connector.Error as err:
        print(f"Error fetching data: {err}")
    finally:
        cursor.close()

def batch_processing(connection, batch_size):
    """
    A generator function that processes each batch to filter users over the age of 25.
    It yields each matching user one by one.

    """
    for batch in stream_users_in_batches(connection, batch_size):        
        for user in batch:            
            if user[3] > 25:
                yield user

if __name__ == '__main__':
    
    connection_db = sd.connect_to_prodev()

    if connection_db:
        try:
            BATCH_SIZE = 50
            print(f"\nProcessing users in batches of {BATCH_SIZE}...")
            
            filtered_users = batch_processing(connection_db, BATCH_SIZE)
            
            for user in filtered_users:
                user_id, name, email, age = user
                print(f"User ID: {user_id}, Name: {name}, Email: {email}, Age: {age}")
                
        finally:
            connection_db.close()
            print("\nDatabase connection closed.")
