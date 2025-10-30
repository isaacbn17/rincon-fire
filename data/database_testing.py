import database_manager

def create_database():
    db = database_manager.DatabaseManager()
    db.create_database()
    db.create_tables()

if __name__ == "__main__":
    create_database()