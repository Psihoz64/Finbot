# tests/test_logic.py
"""Тесты бизнес-логики"""

import logging
from typing import Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def check_balance_calculation() -> Tuple[bool, str]:
    """Проверяет корректность расчёта баланса"""
    test_user_id = 999999998
    
    try:
        from database import add_transaction, get_total_balance, get_db_connection
        
        # Очищаем тестовые данные
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE user_id = ?", (test_user_id,))
            cursor.execute("DELETE FROM savings_balance WHERE user_id = ?", (test_user_id,))
            conn.commit()
        
        # Добавляем тестовые данные:
        # Доход: 1000
        # Расход: 300
        # Пополнение накоплений: 200
        # Снятие с накоплений: 50
        
        add_transaction(test_user_id, 'income', 'Зарплата', 1000)
        add_transaction(test_user_id, 'expense', 'Еда', 300)
        add_transaction(test_user_id, 'saving', 'Пополнение', 200, is_saving_withdrawal=False)
        add_transaction(test_user_id, 'saving', 'Снятие', 50, is_saving_withdrawal=True)
        
        # Ожидаемый баланс: 1000 - 300 - 200 + 50 = 550
        expected_balance = 550.0
        
        balance_data = get_total_balance(test_user_id)
        actual_balance = balance_data['current_balance']
        
        # Очищаем тестовые данные
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE user_id = ?", (test_user_id,))
            cursor.execute("DELETE FROM savings_balance WHERE user_id = ?", (test_user_id,))
            conn.commit()
        
        if abs(actual_balance - expected_balance) > 0.01:
            return False, f"Неверный расчёт баланса: ожидалось {expected_balance}, получено {actual_balance}"
        
        # Проверяем баланс накоплений: 200 - 50 = 150
        expected_savings = 150.0
        actual_savings = balance_data['savings_balance']
        
        if abs(actual_savings - expected_savings) > 0.01:
            return False, f"Неверный расчёт накоплений: ожидалось {expected_savings}, получено {actual_savings}"
        
        return True, "Расчёт баланса корректен"
        
    except Exception as e:
        # Очищаем тестовые данные
        try:
            from database import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE user_id = ?", (test_user_id,))
                cursor.execute("DELETE FROM savings_balance WHERE user_id = ?", (test_user_id,))
                conn.commit()
        except:
            pass
        
        return False, f"Ошибка расчёта баланса: {str(e)}"


async def check_currency_rates() -> Tuple[bool, str]:
    """Проверяет доступность курсов валют"""
    try:
        from currency_rates import get_currency_rates
        
        rates = await get_currency_rates()
        
        if not rates:
            return False, "Не удалось получить курсы валют"
        
        # Проверяем наличие основных валют
        required_currencies = ['USD', 'EUR']
        missing = [c for c in required_currencies if c not in rates]
        
        if missing:
            return False, f"Отсутствуют курсы валют: {', '.join(missing)}"
        
        return True, f"Курсы валют доступны: {', '.join(rates.keys())}"
        
    except Exception as e:
        return False, f"Ошибка получения курсов валют: {str(e)}"


def check_handlers_registered() -> Tuple[bool, str]:
    """Проверяет наличие всех необходимых обработчиков"""
    try:
        from handlers.main import handle_main_button
        from handlers.categories import handle_category_selection
        from handlers.saving import handle_saving_button
        from handlers.analytics import handle_analytics_button
        from handlers.transactions import handle_transactions_button
        from handlers.currency import handle_currency_rates
        
        return True, "Все обработчики зарегистрированы"
        
    except ImportError as e:
        return False, f"Ошибка импорта обработчиков: {str(e)}"
    except Exception as e:
        return False, f"Ошибка проверки обработчиков: {str(e)}"


def check_keyboards() -> Tuple[bool, str]:
    """Проверяет корректность клавиатур"""
    try:
        from keyboards import (
            main_menu_keyboard, 
            categories_keyboard,
            analytics_keyboard,
            saving_actions_keyboard
        )
        
        # Проверяем, что клавиатуры создаются без ошибок
        main_kb = main_menu_keyboard()
        if not main_kb.inline_keyboard:
            return False, "Главное меню пустое"
        
        # Проверяем клавиатуры категорий
        income_kb = categories_keyboard('income')
        if not income_kb.inline_keyboard:
            return False, "Клавиатура доходов пустая"
        
        expense_kb = categories_keyboard('expense')
        if not expense_kb.inline_keyboard:
            return False, "Клавиатура расходов пустая"
        
        return True, "Все клавиатуры корректны"
        
    except Exception as e:
        return False, f"Ошибка проверки клавиатур: {str(e)}"