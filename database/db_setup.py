import mysql.connector
from mysql.connector import Error

def create_database_and_table():
    # Update with your MySQL credentials
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '1234' # Local MySQL configuration
    }
    
    try:
        # Connect to MySQL Server (without specifying database yet)
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create Database
            cursor.execute("CREATE DATABASE IF NOT EXISTS grid_trading_db")
            print("Database 'grid_trading_db' created or already exists.")
            
            # Switch to the new database
            cursor.execute("USE grid_trading_db")
            
            # Create Trade Logs Table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS trade_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket INT NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                order_type VARCHAR(10) NOT NULL,
                volume DECIMAL(10, 2) NOT NULL,
                price DECIMAL(10, 5) NOT NULL,
                status VARCHAR(20) NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
            print("Table 'trade_logs' created successfully.")
            
            cursor.close()
            connection.close()
            print("MySQL connection closed.")
            
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")

if __name__ == "__main__":
    create_database_and_table()
