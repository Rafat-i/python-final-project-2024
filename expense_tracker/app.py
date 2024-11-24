from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import io
import matplotlib

from functools import wraps
from flask import request, jsonify

matplotlib.use('Agg')  # Required for non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime

app = Flask(__name__)

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


def get_db():
    conn = sqlite3.connect('expenses.db')
    conn.row_factory = sqlite3.Row  # This enables name-based access to columns
    return conn


@app.route('/')
@check_ip
def index():
    conn = get_db()

    # Get categories for the dropdown
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

    return render_template('index.html',
                           expenses=expenses,
                           categories=categories,
                           budget_overview=budget_overview)


@app.route('/expenses', methods=['POST'])
@check_ip
def add_expense():
    amount = request.form['amount']
    description = request.form['description']
    category_id = request.form['category_id']

    conn = get_db()
    conn.execute('''
        INSERT INTO expenses (amount, description, category_id)
        VALUES (?, ?, ?)
    ''', (amount, description, category_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/expenses/<int:id>', methods=['DELETE'])
@check_ip
def delete_expense(id):
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/expenses/chart')
@check_ip
def expense_chart():
    conn = get_db()
    # Get expenses grouped by category
    expenses = conn.execute('''
        SELECT c.name, SUM(e.amount) as total
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        GROUP BY c.name
    ''').fetchall()
    conn.close()

    # Create pie chart
    categories = [row['name'] for row in expenses]
    amounts = [row['total'] for row in expenses]

    plt.figure(figsize=(10, 8))
    plt.pie(amounts, labels=categories, autopct='%1.1f%%')
    plt.title('Expenses by Category')

    # Save plot to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)

    return send_file(buf, mimetype='image/png')


@app.route('/budgets', methods=['GET', 'POST'])
@check_ip
def manage_budgets():
    conn = get_db()
    if request.method == 'POST':
        # Update budgets
        budgets = request.form.getlist('budget')
        category_ids = request.form.getlist('category_id')
        for category_id, budget in zip(category_ids, budgets):
            conn.execute('''
                UPDATE categories
                SET monthly_budget = ?
                WHERE id = ?
            ''', (budget, category_id))
        conn.commit()

    # Fetch categories and budgets
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    return render_template('budgets.html', categories=categories)


if __name__ == '__main__':
    app.run(debug=True)
