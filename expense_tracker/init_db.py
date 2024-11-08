# init_db.py
import sqlite3
def init_db():
    # Connect to SQLite (creates db file if it doesn't exist)
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Drop tables if they exist
    cursor.execute('''DROP TABLE IF EXISTS expenses''')
    cursor.execute('''DROP TABLE IF EXISTS categories''')
    # Create categories table
    cursor.execute('''
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    # Create expenses table
    cursor.execute('''
    CREATE TABLE expenses (
        id INTEGER PRIMARY KEY,
        amount DECIMAL(10,2) NOT NULL,
        description TEXT,
        category_id INTEGER,
        date DATE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    ''')
    # Insert default categories
    default_categories = [
        ('Groceries',),
        ('Transportation',),
        ('Entertainment',),
        ('Utilities',),
        ('Other',)
    ]
    cursor.executemany('INSERT INTO categories (name) VALUES (?)', default_categories)
    # Commit and close
    conn.commit()
    conn.close()
if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")