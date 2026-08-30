def check_keyboards() -> Tuple[bool, str]:
    """Проверяет корректность клавиатур"""
    try:
        from keyboards import (
            main_menu_keyboard, 
            categories_keyboard,
            analytics_keyboard,
            saving_actions_keyboard
        )
        from database import get_categories
        
        errors = []
        
        # Проверяем главное меню
        try:
            main_kb = main_menu_keyboard()
            if not main_kb or not hasattr(main_kb, 'inline_keyboard'):
                errors.append("Главное меню пустое")
        except Exception as e:
            errors.append(f"Ошибка главного меню: {e}")
        
        # Получаем категории из БД
        try:
            income_categories = get_categories('income')
            expense_categories = get_categories('expense')
        except Exception as e:
            errors.append(f"Не удалось получить категории из БД: {e}")
            income_categories = []
            expense_categories = []
        
        # Проверяем клавиатуру доходов
        try:
            if income_categories:
                income_kb = categories_keyboard(income_categories, 'income')
                if not income_kb or not hasattr(income_kb, 'inline_keyboard'):
                    errors.append("Клавиатура доходов пустая")
            else:
                errors.append("Нет категорий доходов для проверки")
        except Exception as e:
            errors.append(f"Ошибка клавиатуры доходов: {e}")
        
        # Проверяем клавиатуру расходов
        try:
            if expense_categories:
                expense_kb = categories_keyboard(expense_categories, 'expense')
                if not expense_kb or not hasattr(expense_kb, 'inline_keyboard'):
                    errors.append("Клавиатура расходов пустая")
            else:
                errors.append("Нет категорий расходов для проверки")
        except Exception as e:
            errors.append(f"Ошибка клавиатуры расходов: {e}")
        
        # Проверяем остальные клавиатуры
        try:
            analytics_kb = analytics_keyboard()
            if not analytics_kb or not hasattr(analytics_kb, 'inline_keyboard'):
                errors.append("Клавиатура аналитики пустая")
        except Exception as e:
            errors.append(f"Ошибка клавиатуры аналитики: {e}")
        
        try:
            saving_kb = saving_actions_keyboard()
            if not saving_kb or not hasattr(saving_kb, 'inline_keyboard'):
                errors.append("Клавиатура накоплений пустая")
        except Exception as e:
            errors.append(f"Ошибка клавиатуры накоплений: {e}")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "Все клавиатуры корректны"
        
    except Exception as e:
        return False, f"Ошибка проверки клавиатур: {str(e)}"