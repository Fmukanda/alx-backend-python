import seed as sd
import mysql.connector
from mysql.connector import errorcode

# def stream_user_ages()
def stream_user_ages(connection):
    """
    A generator function that fetches ages from the user_data table
    one by one and yields them.

    """
    if connection is None:
        return

    cursor = connection.cursor(buffered=True)
    try:
        query = f"SELECT age FROM {sd.TABLE_NAME}"
        cursor.execute(query)

        # First loop: Iterates over the cursor to yield each age
        for (age,) in cursor:
            yield age
    except mysql.connector.Error as err:
        print(f"Error fetching data: {err}")
    finally:
        cursor.close()

def calculate_average_age(age_generator):
    """
    Calculates the average age from a generator without loading all ages into memory.

    """
    total_age = 0
    user_count = 0
    
    # Second loop: Iterates over the ages from the generator
    for age in age_generator:
        total_age += age
        user_count += 1
    
    if user_count == 0:
        return 0
    
    return total_age / user_count

if __name__ == '__main__':
   
    connection_db = sd.connect_to_prodev()

    if connection_db:
        try:
            ages_stream = stream_user_ages(connection_db)            
            avg_age = calculate_average_age(ages_stream)
            print(f"\nAverage age of users: {avg_age}")
            
        finally:
            connection_db.close()
            print("\nDatabase connection closed.")

