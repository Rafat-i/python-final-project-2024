from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import io
import matplotlib
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

from functools import wraps
from flask import request, jsonify

matplotlib.use('Agg')  # Required for non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime

app = Flask(__name__)

# Load environment variables from the .env file
load_dotenv()
encryption_key = os.getenv('ENCRYPTION_KEY')

# Generate and save encryption key if not exists
if not encryption_key:
    encryption_key = Fernet.generate_key()
    with open('.env', 'w') as f:
        f.write(f'ENCRYPTION_KEY={encryption_key.decode()}')

fernet = Fernet(encryption_key)

# Helper function to encrypt data
def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

# Helper function to decrypt data
def decrypt_data(encrypted_data: str) -> str:
    return fernet.decrypt(encrypted_data.encode()).decode()

# Set of blocked IP addresses
BLOCKED_IPS = set()  # {'127.0.0.1'}

# IP blocking middleware
def check_ip(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.remote_addr in BLOCKED_IPS:
            return jsonify({'error': 'blocked'}), 403
        return f(*args, **kwargs)
    return wrapper


# Helper function to establish a database connection
def get_db():
    conn = sqlite3.connect('expenses.db')
    conn.row_factory = sqlite3.Row  # This enables name-based access to columns
    return conn

# Route for the homepage
@app.route('/')
@check_ip
def index():
    conn = get_db()

    # Get categories for the dropdown menu
    categories = conn.execute('SELECT * FROM categories').fetchall()

    # Get all expenses
    expenses = conn.execute('''
        SELECT e.*, c.name as category_name 
        FROM expenses e 
        JOIN categories c ON e.category_id = c.id 
        ORDER BY e.date DESC
    ''').fetchall()



    # Get monthly budget overview with progress calculation
    budget_overview = conn.execute('''
        SELECT 
            c.name,
            c.monthly_budget,
            COALESCE(SUM(e.amount), 0) AS total_spent
        FROM categories c
        LEFT JOIN expenses e ON c.id = e.category_id
            AND strftime('%Y-%m', e.date) = strftime('%Y-%m', 'now')
        GROUP BY c.id, c.name, c.monthly_budget
    ''').fetchall()

    # Add progress calculations to budget_overview
    budget_overview = [
        {
            **row,
            "progress": min((row["total_spent"] / row["monthly_budget"]) * 100, 100) 
            if row["monthly_budget"] > 0 else 0
        }
        for row in budget_overview
    ]

    conn.close()

    # Render the index page with all data
    print(
        f"Returning index page with {len(expenses)} expenses, {len(categories)} categories, and budget overview: {[dict(row) for row in budget_overview]}")
    return render_template('index.html',
                           expenses=expenses,
                           categories=categories,
                           budget_overview=budget_overview)


# Route to add a new expense
@app.route('/expenses', methods=['POST'])
@check_ip
def add_expense():
    amount = request.form['amount']
    description = encrypt_data(request.form['description'])
    category_id = request.form['category_id']

    print(f"Attempting to insert expense: amount={amount}, description='{description}', category_id={category_id}")

    # Insert the new expense into the database
    conn = get_db()
    conn.execute('''
        INSERT INTO expenses (amount, description, category_id)
        VALUES (?, ?, ?)
    ''', (amount, description, category_id))
    conn.commit()
    print(f"Expense inserted successfully: amount={amount}, description='{description}', category_id={category_id}")
    conn.close()

    # Redirect back to the homepage
    return redirect(url_for('index'))

# Route to delete an expense
@app.route('/expenses/<int:id>', methods=['DELETE'])
@check_ip
def delete_expense(id):
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# This is an API endpoint for generating a pie chart of expenses
# API endpoint to generate and return a pie chart of expenses grouped by category.
# Returns: A PNG image of a pie chart.
@app.route('/expenses/chart')
@check_ip
def expense_chart():
    print(f"GET /expenses/chart endpoint hit by {request.remote_addr}")
    conn = get_db()
    # Get expenses grouped by category
    expenses = conn.execute('''
            SELECT c.name, SUM(e.amount) as total
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
            GROUP BY c.name
        ''').fetchall()
    print(f"Fetched expenses for chart: {expenses}")
    conn.close()

    # Prepare data for the chart
    categories = [row['name'] for row in expenses] # Extract category names
    amounts = [row['total'] for row in expenses] # Extract corresponding total amounts

    # Create pie chart
    plt.figure(figsize=(10, 8)) # Set the figure size (10x8 inches)
    wedges, texts, autotexts = plt.pie(
        amounts, # Data for the pie chart
        labels=categories, # Labels for each slice of the pie
        autopct=lambda pct: f'{pct:.1f}%\n(${pct / 100 * sum(amounts):,.2f})',  # Format to show percentage and actual amount
        textprops={'fontsize': 10} # Font size for the labels
    )
    plt.title('Expenses by Category') # Set the title for the chart

    # Save the chart to a bytes buffer instead of a file
    buf = io.BytesIO() # Create an in-memory buffer to store the chart image
    plt.savefig(buf, format='png', bbox_inches='tight') # Save the chart as a PNG image
    plt.close() # Close the plot to free memory
    buf.seek(0) # Move the cursor in the buffer back to the start

    # Return the chart image as a PNG image
    print(f"Generated chart with categories: {categories} and amounts: {amounts}")
    return send_file(buf, mimetype='image/png')


# Route to manage budgets
@app.route('/budgets', methods=['GET', 'POST'])
@check_ip
def manage_budgets():
    conn = get_db()
    if request.method == 'POST':
        # Update budgets for each category
        budgets = request.form.getlist('budget')
        category_ids = request.form.getlist('category_id')
        for category_id, budget in zip(category_ids, budgets):
            conn.execute('''
                UPDATE categories
                SET monthly_budget = ?
                WHERE id = ?
            ''', (budget, category_id))
        conn.commit()

    # Fetch categories and their budgets
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    return render_template('budgets.html', categories=categories)


if __name__ == '__main__':
    app.run(debug=True)
