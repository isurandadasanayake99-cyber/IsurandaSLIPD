import mysql.connector
from mysql.connector import Error

class DatabaseLogger:
    def __init__(self):
        # Ensure password matches your local MySQL setup
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '1234', 
            'database': 'grid_trading_db'
        }
    
    def log_trade(self, ticket, symbol, order_type, volume, price, status):
        """
        Connects to the database and inserts a new trade log entry.
        Since each thread utilizes this method, we open and close a connection
        each time to keep it thread-safe without complex pooling.
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor()
                query = """
                INSERT INTO trade_logs (ticket, symbol, order_type, volume, price, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (ticket, symbol, order_type, volume, price, status))
                connection.commit()
                cursor.close()
                connection.close()
        except Error as e:
            print(f"Database error while logging trade for {symbol}: {e}")

    def fetch_recent_logs(self, symbol=None, limit=50):
        """
        Fetches the latest trade logs from MySQL.
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                if symbol and symbol != "ALL":
                    query = "SELECT * FROM trade_logs WHERE symbol = %s ORDER BY id DESC LIMIT %s"
                    cursor.execute(query, (symbol, limit))
                else:
                    query = "SELECT * FROM trade_logs ORDER BY id DESC LIMIT %s"
                    cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                cursor.close()
                connection.close()
                return rows
        except Error as e:
            # print(f"Error fetching logs: {e}")
            return []
        return []

    def get_summary_stats(self):
        """
        Returns total trades count, symbols traded, and total volume.
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS total_trades, IFNULL(SUM(volume), 0) AS total_volume FROM trade_logs")
                stats = cursor.fetchone()
                cursor.close()
                connection.close()
                return stats or {"total_trades": 0, "total_volume": 0.0}
        except Error:
            return {"total_trades": 0, "total_volume": 0.0}
        return {"total_trades": 0, "total_volume": 0.0}

    def clear_logs(self):
        """
        Clears all trade logs from MySQL.
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor()
                cursor.execute("TRUNCATE TABLE trade_logs")
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error:
            return False
        return False
