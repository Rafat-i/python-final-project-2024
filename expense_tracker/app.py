# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import io
import matplotlib

matplotlib.use('Agg')  # Required for non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect('expenses.db')
    conn.row_factory = sqlite3.Row  # This enables name-based access to columns
    return conn


@app.route('/')
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
    conn.close()
    return render_template('index.html', expenses=expenses, categories=categories)


@app.route('/expenses', methods=['POST'])
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
def delete_expense(id):
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/expenses/chart')
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


if __name__ == '__main__':
    app.run(debug=True)