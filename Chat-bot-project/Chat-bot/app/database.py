import sqlite3
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = 'chatbot.db'):
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as list of dicts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                raise

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute UPDATE/INSERT query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                logger.error(f"Database update error: {str(e)}")
                raise

    def get_table_schema(self, table_name: str = None) -> Dict[str, Any]:
        """Get schema for specific table or all tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if table_name:
                # Get schema for specific table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                return {
                    "table": table_name,
                    "columns": [dict(col) for col in columns]
                }
            else:
                # Get all tables and their schemas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = cursor.fetchall()

                result = {}
                for table in tables:
                    table_name = table['name']
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    result[table_name] = {
                        "columns": [dict(col) for col in columns]
                    }

                return result

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample data from table"""
        return self.execute_query(f"SELECT * FROM {table_name} LIMIT ?", (limit,))

    def _init_database(self):
        """Initialize database with sample data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create tables
            tables = {
                'users': '''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''',
                'products': '''
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        price REAL NOT NULL,
                        stock_quantity INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''',
                'orders': '''
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT CHECK(status IN ('pending', 'shipped', 'delivered', 'cancelled')) DEFAULT 'pending',
                        total_amount REAL NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''',
                'order_items': '''
                    CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        unit_price REAL NOT NULL,
                        subtotal REAL GENERATED ALWAYS AS (quantity * unit_price) STORED,
                        FOREIGN KEY (order_id) REFERENCES orders(id),
                        FOREIGN KEY (product_id) REFERENCES products(id)
                    )
                ''',
                'payments': '''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER UNIQUE NOT NULL,
                        payment_method TEXT CHECK(payment_method IN ('credit_card', 'debit_card', 'paypal', 'cash')) DEFAULT 'credit_card',
                        payment_status TEXT CHECK(payment_status IN ('pending', 'completed', 'failed', 'refunded')) DEFAULT 'pending',
                        amount REAL NOT NULL,
                        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(id)
                    )
                '''
            }

            for table_name, create_sql in tables.items():
                cursor.execute(create_sql)

            # Insert sample data if empty
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                self._insert_sample_data(cursor)
                conn.commit()
                logger.info("Database initialized with sample data")

    def _insert_sample_data(self, cursor):
        """Insert sample data into database"""
        # Insert users
        users = [
            ('john.doe@example.com', 'John Doe'),
            ('jane.smith@example.com', 'Jane Smith'),
            ('robert.johnson@example.com', 'Robert Johnson'),
            ('sarah.williams@example.com', 'Sarah Williams'),
            ('michael.brown@example.com', 'Michael Brown')
        ]
        for email, name in users:
            cursor.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))

        # Insert products
        products = [
            ('MacBook Pro 16"', 'Electronics', 2399.99, 25),
            ('iPhone 15 Pro', 'Electronics', 999.99, 50),
            ('Sony WH-1000XM5 Headphones', 'Electronics', 399.99, 100),
            ('Dell XPS 13', 'Electronics', 1299.99, 30),
            ('Samsung Galaxy S24', 'Electronics', 899.99, 75),
            ('Coffee Maker', 'Home & Kitchen', 89.99, 150),
            ('Blender', 'Home & Kitchen', 79.99, 120),
            ('Air Fryer', 'Home & Kitchen', 129.99, 80),
            ('Office Chair', 'Furniture', 199.99, 60),
            ('Desk', 'Furniture', 299.99, 40),
            ('Python Programming Book', 'Books', 49.99, 200),
            ('Data Science Handbook', 'Books', 79.99, 150),
            ('Yoga Mat', 'Sports', 29.99, 300),
            ('Dumbbell Set', 'Sports', 99.99, 100),
            ('Winter Jacket', 'Clothing', 129.99, 120),
            ('Running Shoes', 'Clothing', 89.99, 200),
            ('Board Game', 'Toys & Games', 39.99, 180),
            ('Lego Set', 'Toys & Games', 79.99, 90)
        ]
        for name, category, price, stock in products:
            cursor.execute(
                "INSERT INTO products (name, category, price, stock_quantity) VALUES (?, ?, ?, ?)",
                (name, category, price, stock)
            )

        # Insert orders
        orders = [
            (1, '2024-01-15 10:30:00', 'delivered', 2399.99),
            (1, '2024-01-20 14:45:00', 'shipped', 129.99),
            (2, '2024-01-10 09:15:00', 'delivered', 1799.98),
            (2, '2024-01-25 16:20:00', 'pending', 399.99),
            (3, '2024-01-05 11:00:00', 'delivered', 329.97),
            (3, '2024-01-18 13:30:00', 'cancelled', 89.99),
            (4, '2024-01-22 15:45:00', 'shipped', 1299.99),
            (5, '2024-01-12 12:00:00', 'delivered', 199.99),
            (1, '2024-01-28 09:30:00', 'pending', 899.99),
            (2, '2024-01-29 14:00:00', 'shipped', 259.98)
        ]
        for user_id, order_date, status, total in orders:
            cursor.execute(
                "INSERT INTO orders (user_id, order_date, status, total_amount) VALUES (?, ?, ?, ?)",
                (user_id, order_date, status, total)
            )

        # Insert order items
        order_items = [
            (1, 1, 1, 2399.99),
            (2, 15, 1, 129.99),
            (3, 2, 1, 999.99),
            (3, 11, 1, 49.99),
            (3, 16, 1, 89.99),
            (3, 6, 1, 89.99),
            (4, 3, 1, 399.99),
            (5, 4, 1, 1299.99),
            (6, 7, 1, 79.99),
            (7, 9, 1, 199.99),
            (7, 10, 1, 299.99),
            (7, 13, 1, 29.99),
            (7, 14, 1, 99.99),
            (7, 17, 1, 39.99),
            (7, 18, 1, 79.99),
            (8, 12, 1, 79.99),
            (8, 11, 1, 49.99),
            (8, 16, 1, 89.99),
            (9, 5, 1, 899.99),
            (10, 15, 2, 129.99)
        ]
        for order_id, product_id, quantity, unit_price in order_items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (order_id, product_id, quantity, unit_price)
            )

        # Insert payments
        payments = [
            (1, 'credit_card', 'completed', 2399.99, '2024-01-15 10:35:00'),
            (2, 'paypal', 'completed', 129.99, '2024-01-20 14:50:00'),
            (3, 'credit_card', 'completed', 1799.98, '2024-01-10 09:20:00'),
            (4, 'credit_card', 'pending', 399.99, '2024-01-25 16:25:00'),
            (5, 'debit_card', 'completed', 329.97, '2024-01-05 11:05:00'),
            (6, 'credit_card', 'refunded', 89.99, '2024-01-18 13:35:00'),
            (7, 'paypal', 'completed', 1299.99, '2024-01-22 15:50:00'),
            (8, 'credit_card', 'completed', 199.99, '2024-01-12 12:05:00'),
            (9, 'credit_card', 'pending', 899.99, '2024-01-28 09:35:00'),
            (10, 'paypal', 'completed', 259.98, '2024-01-29 14:05:00')
        ]
        for order_id, method, status, amount, paid_at in payments:
            cursor.execute(
                "INSERT INTO payments (order_id, payment_method, payment_status, amount, paid_at) VALUES (?, ?, ?, ?, ?)",
                (order_id, method, status, amount, paid_at)
            )