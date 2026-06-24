import sqlite3
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from contextlib import contextmanager

DB_NAME = "finance.db"

@contextmanager
def get_db_connection():
    """Контекстный менеджер для работы с БД"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Инициализация базы данных"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_saving_withdrawal BOOLEAN DEFAULT 0
            )
        ''')
        
        # Таблица для хранения баланса накоплений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS savings_balance (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0
            )
        ''')
        
        # Таблица для категорий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(type, name)
            )
        ''')
        
        conn.commit()


def init_categories():
    """Инициализация категорий по умолчанию"""
    from categories import INCOME_CATEGORIES, EXPENSE_CATEGORIES
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        
        if count == 0:
            for category in INCOME_CATEGORIES:
                cursor.execute(
                    "INSERT INTO categories (type, name) VALUES (?, ?)",
                    ('income', category)
                )
            
            for category in EXPENSE_CATEGORIES:
                cursor.execute(
                    "INSERT INTO categories (type, name) VALUES (?, ?)",
                    ('expense', category)
                )
            
            conn.commit()
            print("✅ Категории успешно загружены в БД")
        else:
            print(f"ℹ️ Категории уже существуют в БД (найдено {count} записей)")


def get_categories(category_type: str = None) -> List[str]:
    """Получение списка категорий из БД"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if category_type:
            cursor.execute(
                "SELECT name FROM categories WHERE type = ? AND is_active = 1 ORDER BY name",
                (category_type,)
            )
            return [row['name'] for row in cursor.fetchall()]
        else:
            cursor.execute(
                "SELECT name, type FROM categories WHERE is_active = 1 ORDER BY type, name"
            )
            return [dict(row) for row in cursor.fetchall()]


def add_transaction(user_id: int, type: str, category: str, 
                    amount: float, description: str = "", 
                    is_saving_withdrawal: bool = False):
    """Добавление новой транзакции"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions 
            (user_id, type, category, amount, description, is_saving_withdrawal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, type, category, amount, description, is_saving_withdrawal))
        
        if type == 'saving':
            if not is_saving_withdrawal:
                cursor.execute('''
                    INSERT INTO savings_balance (user_id, balance)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET 
                    balance = balance + ?
                ''', (user_id, amount, amount))
            else:
                cursor.execute('''
                    UPDATE savings_balance 
                    SET balance = balance - ?
                    WHERE user_id = ?
                ''', (amount, user_id))
        
        conn.commit()
        return cursor.lastrowid


def get_transactions(user_id: int, limit: int = 50, 
                     start_date: str = None, end_date: str = None) -> List[Dict]:
    """Получение транзакций пользователя"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = [user_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
            
        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_savings_balance(user_id: int) -> float:
    """Получение баланса накоплений"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance FROM savings_balance WHERE user_id = ?", 
            (user_id,)
        )
        row = cursor.fetchone()
        return row['balance'] if row else 0.0


def get_total_balance(user_id: int) -> Dict:
    """Расчет общего баланса пользователя"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'income'",
            (user_id,)
        )
        total_income = cursor.fetchone()[0] or 0
        
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'expense'",
            (user_id,)
        )
        total_expense = cursor.fetchone()[0] or 0
        
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'saving' AND is_saving_withdrawal = 0",
            (user_id,)
        )
        total_saved = cursor.fetchone()[0] or 0
        
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'saving' AND is_saving_withdrawal = 1",
            (user_id,)
        )
        total_withdrawn = cursor.fetchone()[0] or 0
        
        current_balance = total_income - total_expense - total_saved + total_withdrawn
        savings_balance = get_savings_balance(user_id)
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'total_saved': total_saved,
            'total_withdrawn': total_withdrawn,
            'current_balance': current_balance,
            'savings_balance': savings_balance
        }


def get_analytics(user_id: int, period: str = "Месяц") -> Dict:
    """Получение аналитики за период"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if period == "Месяц":
            date_filter = "datetime(date) >= datetime('now', 'start of month')"
        elif period == "Год":
            date_filter = "datetime(date) >= datetime('now', 'start of year')"
        else:
            date_filter = "1=1"
        
        cursor.execute(f'''
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND type = 'income' AND {date_filter}
            GROUP BY category
        ''', (user_id,))
        income_by_category = {row['category']: row['total'] for row in cursor.fetchall()}
        
        cursor.execute(f'''
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND type = 'expense' AND {date_filter}
            GROUP BY category
        ''', (user_id,))
        expense_by_category = {row['category']: row['total'] for row in cursor.fetchall()}
        
        cursor.execute(f'''
            SELECT 
                SUM(CASE WHEN type = 'saving' AND is_saving_withdrawal = 0 THEN amount ELSE 0 END) as total_saved,
                SUM(CASE WHEN type = 'saving' AND is_saving_withdrawal = 1 THEN amount ELSE 0 END) as total_withdrawn
            FROM transactions
            WHERE user_id = ? AND {date_filter}
        ''', (user_id,))
        
        saving_row = cursor.fetchone()
        total_saved = saving_row['total_saved'] or 0
        total_withdrawn = saving_row['total_withdrawn'] or 0
        
        return {
            'income_by_category': income_by_category,
            'expense_by_category': expense_by_category,
            'total_income': sum(income_by_category.values()),
            'total_expense': sum(expense_by_category.values()),
            'total_saved': total_saved,
            'total_withdrawn': total_withdrawn,
            'balance': get_savings_balance(user_id)
        }


def check_month_has_data(user_id: int, year: int, month: int) -> bool:
    """
    Проверяет, есть ли транзакции за указанный месяц
    """
    if month < 1 or month > 12:
        return False
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        cursor.execute(
            """
            SELECT COUNT(*) FROM transactions 
            WHERE user_id = ? 
            AND date >= ? 
            AND date < ?
            """,
            (user_id, start_date, end_date)
        )
        
        count = cursor.fetchone()[0]
        return count > 0


def get_analytics_for_month(user_id: int, year: int, month: int) -> Dict:
    """
    Получение аналитики за конкретный месяц
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        cursor.execute(
            """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND type = 'income' 
            AND date >= ? AND date < ?
            GROUP BY category
            """,
            (user_id, start_date, end_date)
        )
        income_by_category = {row['category']: row['total'] for row in cursor.fetchall()}
        
        cursor.execute(
            """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND type = 'expense' 
            AND date >= ? AND date < ?
            GROUP BY category
            """,
            (user_id, start_date, end_date)
        )
        expense_by_category = {row['category']: row['total'] for row in cursor.fetchall()}
        
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN type = 'saving' AND is_saving_withdrawal = 0 THEN amount ELSE 0 END) as total_saved,
                SUM(CASE WHEN type = 'saving' AND is_saving_withdrawal = 1 THEN amount ELSE 0 END) as total_withdrawn
            FROM transactions
            WHERE user_id = ? 
            AND date >= ? AND date < ?
            """,
            (user_id, start_date, end_date)
        )
        
        saving_row = cursor.fetchone()
        total_saved = saving_row['total_saved'] or 0
        total_withdrawn = saving_row['total_withdrawn'] or 0
        
        savings_balance = get_savings_balance(user_id)
        
        total_income = sum(income_by_category.values())
        total_expense = sum(expense_by_category.values())
        current_balance = total_income - total_expense - total_saved + total_withdrawn
        
        return {
            'income_by_category': income_by_category,
            'expense_by_category': expense_by_category,
            'total_income': total_income,
            'total_expense': total_expense,
            'total_saved': total_saved,
            'total_withdrawn': total_withdrawn,
            'balance': savings_balance,
            'current_balance': current_balance
        }