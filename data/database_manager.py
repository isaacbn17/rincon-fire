import mysql.connector
from mysql.connector import Error
from pathlib import Path

class DatabaseManager:
    DATABASE_NAME = None
    USER = None
    PASSWORD = None
    HOST = None
    PORT = None

    try:
        props_path = Path(__file__).parent / "db.properties"

        if not props_path.exists():
            raise FileNotFoundError("Unable to load db.properties")

        with open(props_path, encoding="utf-8") as f:
            properties = dict(
                line.strip().split("=", 1)
                for line in f
                if line.strip() and not line.startswith("#")
            )

            DATABASE_NAME = properties["db.name"]
            USER = properties["db.user"]
            PASSWORD = properties["db.password"]
            HOST = properties["db.host"]
            PORT = int(properties["db.port"])

    except Exception as ex:
        raise RuntimeError(f"Unable to process db.properties: {ex}") from ex


    @staticmethod
    def create_database():
        """Create the database if it doesn't exist"""
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(
                host = DatabaseManager.HOST,
                port = DatabaseManager.PORT,
                user = DatabaseManager.USER,
                password = DatabaseManager.PASSWORD,
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DatabaseManager.DATABASE_NAME}")
            conn.commit()
        except Error as e:
            raise Exception(e)
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()


    @staticmethod
    def get_connection():
        """Get a connection to the database."""
        try:
            conn = mysql.connector.connect(
                host=DatabaseManager.HOST,
                port=DatabaseManager.PORT,
                user=DatabaseManager.USER,
                password=DatabaseManager.PASSWORD,
                database=DatabaseManager.DATABASE_NAME,
            )
            return conn
        except Error as e:
            raise Exception(e)


    @staticmethod
    def create_tables():
        """Create necessary tables if they don't exist."""
        conn = None
        cursor = None
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wildfire_location_prediction (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    station_id VARCHAR(10) NOT NULL,
                    station_name VARCHAR(100) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    confidence INT NOT NULL,
                    weather_json JSON
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS satellite_image (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    prediction_id INT NOT NULL,
                    image_path VARCHAR(255) NOT NULL,
                    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prediction_id)
                        REFERENCES wildfire_location_prediction(id)
                        ON DELETE CASCADE
                )
            """)

            conn.commit()

        except Error as e:
            raise Exception(e)
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

