from database import Database, Base

def init_db():
    db = Database()
    db.init_db()
    print("Datenbank wurde erfolgreich initialisiert")

if __name__ == '__main__':
    init_db() 