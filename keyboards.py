from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ANALYTICS_PERIODS
from database import get_categories

def main_menu_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("💰 Доходы", callback_data="income")],
        [InlineKeyboardButton("💸 Расходы", callback_data="expense")],
        [InlineKeyboardButton("🏦 Накопления", callback_data="saving")],
        [InlineKeyboardButton("📊 Аналитика", callback_data="analytics")],
        [InlineKeyboardButton("📋 Мои транзакции", callback_data="transactions")],
        [InlineKeyboardButton("💳 Баланс", callback_data="balance")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def categories_keyboard(categories, action_type):
    """Клавиатура с категориями (с эмодзи)"""
    keyboard = []
    row = []
    for i, category in enumerate(categories):
        # Категории уже содержат эмодзи из categories.py
        row.append(InlineKeyboardButton(category, callback_data=f"{action_type}_{category}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def analytics_keyboard():
    """Клавиатура для выбора периода аналитики"""
    keyboard = [
        [InlineKeyboardButton("📅 Месяц", callback_data="analytics_Месяц")],
        [InlineKeyboardButton("📆 Год", callback_data="analytics_Год")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def saving_actions_keyboard():
    """Клавиатура для действий с накоплениями"""
    keyboard = [
        [InlineKeyboardButton("➕ Пополнить", callback_data="saving_add")],
        [InlineKeyboardButton("➖ Снять", callback_data="saving_withdraw")],
        [InlineKeyboardButton("📊 Баланс", callback_data="saving_balance")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)