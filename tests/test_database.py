# tests/test_database.py
"""Тесты базы данных"""

import sqlite3
import logging
from typing import Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def check_database_structure() -> Tuple[bool, str]:
    """Проверяет структуру базы данных"""
    try:
        from database import get_db_connection
        
        required_tables = ['transactions', 'savings_balance', 'categories']
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем список таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row['name'] for row in cursor.fetchall()]
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                return False, f"Отсутствуют таблицы: {', '.join(missing_tables)}"
            
            # Проверяем структуру таблицы transactions
            cursor.execute("PRAGMA table_info(transactions)")
            columns = {row['name'] for row in cursor.fetchall()}
            
            required_columns = {'id', 'user_id', 'type', 'category', 'amount', 
                              'description', 'date', 'is_saving_withdrawal'}
            missing_columns = required_columns - columns
            
            if missing_columns:
                return False, f"Отсутствуют колонки в transactions: {', '.join(missing_columns)}"
        
        return True, "Структура БД корректна"
        
    except Exception as e:
        return False, f"Ошибка проверки структуры БД: {str(e)}"


def check_categories() -> Tuple[bool, str]:
    """Проверяет наличие категорий"""
    try:
        from database import get_categories
        
        income_categories = get_categories('income')
        expense_categories = get_categories('expense')
        
        if not income_categories:
            return False, "Нет категорий доходов"
        
        if not expense_categories:
            return False, "Нет категорий расходов"
        
        return True, f"Категории: {len(income_categories)} доходов, {len(expense_categories)} расходов"
        
    except Exception as e:
        return False, f"Ошибка проверки категорий: {str(e)}"


def check_crud_operations() -> Tuple[bool, str]:
    """Проверяет CRUD операции с тестовыми данными"""
    test_user_id = 999999999  # Тестовый user_id
    test_amount = 123.45
    test_category = "Тестовая категория"
    
    try:
        from database import add_transaction, get_transactions, get_total_balance
        
        # 1. CREATE - добавляем тестовую транзакцию
        transaction_id = add_transaction(
            user_id=test_user_id,
            type='income',
            category=test_category,
            amount=test_amount,
            description="Тестовая транзакция"
        )
        
        if not transaction_id:
            return False, "Не удалось создать тестовую транзакцию"
        
        # 2. READ - читаем транзакции
        transactions = get_transactions(test_user_id, limit=10)
        if not transactions:
            return False, "Не удалось прочитать тестовые транзакции"
        
        # Проверяем, что наша транзакция есть
        found = any(t['id'] == transaction_id for t in transactions)
        if not found:
            return False, "Созданная транзакция не найдена при чтении"
        
        # 3. Проверяем расчёт баланса
        balance_data = get_total_balance(test_user_id)
        if abs(balance_data['current_balance'] - test_amount) > 0.01:
            return False, f"Неверный расчёт баланса: ожидалось {test_amount}, получено {balance_data['current_balance']}"
        
        # 4. DELETE - удаляем тестовые данные
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE user_id = ?", (test_user_id,))
            cursor.execute("DELETE FROM savings_balance WHERE user_id = ?", (test_user_id,))
            conn.commit()
        
        return True, "CRUD операции работают корректно"
        
    except Exception as e:
        # Пытаемся очистить тестовые данные
        try:
            from database import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE user_id = ?", (test_user_id,))
                cursor.execute("DELETE FROM savings_balance WHERE user_id = ?", (test_user_id,))
                conn.commit()
        except:
            pass
        
        return False, f"Ошибка CRUD операций: {str(e)}"