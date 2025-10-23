import mysql.connector
from mysql.connector import Error
from pathlib import Path

class DataAccessException(Exception):
    print(f"An exception occurred: {Exception}")

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

            host = properties["db.host"]
            port = int(properties["db.port"])

    except Exception as ex:
        raise RuntimeError(f"Unable to process db.properties: {ex}") from ex


    @staticmethod
    def create_database():
        """Create the database if it doesn't exist"""
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
            raise DataAccessException(e)
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
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
            raise DataAccessException(e)
