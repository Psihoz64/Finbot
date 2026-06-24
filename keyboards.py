from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ANALYTICS_PERIODS
from database import get_categories
from datetime import datetime, timedelta

def main_menu_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("💰 Доходы", callback_data="income"), 
         InlineKeyboardButton("💸 Расходы", callback_data="expense")],
        [InlineKeyboardButton("🏦 Накопления", callback_data="saving"), 
         InlineKeyboardButton("📊 Аналитика", callback_data="analytics")],
        [InlineKeyboardButton("📋 Транзакции", callback_data="transactions"), 
         InlineKeyboardButton("💳 Баланс", callback_data="balance"),
         InlineKeyboardButton("ℹ️", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def categories_keyboard(categories, action_type):
    """Клавиатура с категориями"""
    keyboard = []
    row = []
    for i, category in enumerate(categories):
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
        [InlineKeyboardButton("📅 Текущий месяц", callback_data="analytics_месяц")],
        [InlineKeyboardButton("📆 Текущий год", callback_data="analytics_год")],
        [InlineKeyboardButton("📅 Выбрать месяц", callback_data="analytics_choose_month")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def month_navigation_keyboard(year: int, month: int, has_prev: bool = True):
    """Клавиатура для навигации по месяцам"""
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    keyboard = [
        [
            InlineKeyboardButton("◀️", callback_data="month_prev") if has_prev else InlineKeyboardButton(" ", callback_data="noop"),
            InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="noop"),
            InlineKeyboardButton("▶️", callback_data="month_next")
        ],
        [InlineKeyboardButton("📊 Показать отчет", callback_data=f"month_show_{year}_{month:02d}")],
        [InlineKeyboardButton("↩️ Назад", callback_data="analytics")]
    ]
    return InlineKeyboardMarkup(keyboard)

def saving_actions_keyboard():
    """Клавиатура для действий с накоплениями"""
    keyboard = [
        [InlineKeyboardButton("➕ Пополнить", callback_data="saving_add")],
        [InlineKeyboardButton("➖ Снять", callback_data="saving_withdraw")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)