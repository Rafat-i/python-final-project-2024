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
        name TEXT NOT NULL UNIQUE,
        monthly_budget DECIMAL(10,2) NOT NULL
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
    # Insert default categories with names and monthly budgets
    default_categories = [
        ('Groceries', 500.00),
        ('Transportation', 200.00),
        ('Entertainment', 150.00),
        ('Utilities', 300.00),
        ('Other', 100.00)
    ]
    cursor.executemany('INSERT INTO categories (name, monthly_budget) VALUES (?, ?)', default_categories)
    # Commit and close
    conn.commit()
    conn.close()
if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
