import mysql.connector
from mysql.connector import Error
import csv
import uuid

DB_HOST = "localhost"
DB_USER = "Fernandes"
DB_PASSWORD = "root"
DB_NAME = "ALX_prodev"
TABLE_NAME = "user_data"

FILE_PATH = r'C:\Users\LENOVO\Desktop\alx-backend-python\docs\user_data.csv'

def connect_db():
    """
    Connects to the MySQL database server.

    """
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("Successfully connected to the MySQL server.")
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None


def create_database(connection):
    """
    Creates the database ALX_prodev if it does not exist.

    """
    if connection is None:
        return
    
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database '{DB_NAME}' created or already exists.")
    except mysql.connector.Error as err:
        print(f"Failed creating database: {err}")
    finally:
        cursor.close()


def connect_to_prodev():
    """
    Connects to the ALX_prodev database in MySQL..

    """
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print(f"Successfully connected to the '{DB_NAME}' database.")
        return connection
    except mysql.connector.Error as err:
        print(f"Failed to connect to '{DB_NAME}': {err}")
        return None

def create_table(connection):
    """
    Creates the user_data table with the specified fields if it does not exist.

    """
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        table_creation_query = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            user_id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            age DECIMAL(5, 2) NOT NULL
        )
        """
        cursor.execute(table_creation_query)
        print(f"Table '{TABLE_NAME}' created or already exists.")
    except mysql.connector.Error as err:
        print(f"Failed creating table: {err}")
    finally:
        cursor.close()


def insert_data(connection, data):
    """
    Inserts data into the user_data table.

    """
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        # Check if data with the same email already exists
        email_check_query = f"SELECT user_id FROM {TABLE_NAME} WHERE email = %s"
        cursor.execute(email_check_query, (data[1],))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"Data for email '{data[1]}' already exists. Skipping insertion.")
        else:
            # Generate a new UUID for the user_id
            user_id = str(uuid.uuid4())
            
            insert_query = f"""
            INSERT INTO {TABLE_NAME} (user_id, name, email, age)
            VALUES (%s, %s, %s, %s)
            """
            # Combine the generated UUID with the provided data
            data_to_insert = (user_id,) + data
            
            cursor.execute(insert_query, data_to_insert)
            connection.commit()
            print("Data inserted successfully.")
            
    except mysql.connector.Error as err:
        print(f"Failed to insert data: {err}")
        connection.rollback()
    finally:
        cursor.close()

def insert_data_from_csv(connection, file_path):
    """
    Reads data from a CSV file and inserts it into the user_data table.

    """
    if connection is None:
        print("Database connection not established. Cannot insert from CSV.")
        return

    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            # Skip the header row
            next(reader, None)
            
            for row in reader:
                # Assuming the CSV has columns in the order: name, email, age
                if len(row) == 3:
                    try:
                        name = row[0]
                        email = row[1]
                        age = float(row[2])
                        insert_data(connection, (name, email, age))
                    except (ValueError, IndexError) as e:
                        print(f"Skipping malformed row: {row}. Error: {e}")
                else:
                    print(f"Skipping malformed row: {row}. Expected 3 values, got {len(row)}.")
        print("Database connection established. CSV data inserted in user_table.")            
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred while reading the CSV file: {e}")

myconnection = connect_to_prodev()
insert_data_from_csv(myconnection, FILE_PATH)

if __name__ == '__main__':
    connection_server = connect_db()

    if connection_server:
        try:
            create_database(connection_server)
        finally:
            connection_server.close()

    connection_db = connect_to_prodev()

    if connection_db:
        try:
            create_table(connection_db)
            
            insert_data_from_csv(connection_db, FILE_PATH)
            
        finally:
            connection_db.close()