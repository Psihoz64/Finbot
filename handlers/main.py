# handlers/main.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from database import get_total_balance, get_categories
from keyboards import main_menu_keyboard, categories_keyboard, analytics_keyboard
from .utils import safe_edit_message

logger = logging.getLogger(__name__)

# === ФУНКЦИИ ===

async def handle_income_selection(query, context: ContextTypes.DEFAULT_TYPE):
    categories = get_categories('income')
    if not categories:
        await safe_edit_message(query, "❌ Нет категорий доходов.", reply_markup=main_menu_keyboard())
        return
    await safe_edit_message(
        query,
        "💰 Выберите категорию дохода:",
        reply_markup=categories_keyboard(categories, 'income'),
        parse_mode='Markdown'
    )

async def handle_expense_selection(query, context: ContextTypes.DEFAULT_TYPE):
    categories = get_categories('expense')
    if not categories:
        await safe_edit_message(query, "❌ Нет категорий расходов.", reply_markup=main_menu_keyboard())
        return
    await safe_edit_message(
        query,
        "💸 Выберите категорию расхода:",
        reply_markup=categories_keyboard(categories, 'expense'),
        parse_mode='Markdown'
    )

async def handle_back(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    balance_data = get_total_balance(user_id)
    text = (
        f"📋 *Главное меню*\n\n"
        f"💰 Баланс: {balance_data['current_balance']:.2f} руб.\n"
        f"🏦 Накопления: {balance_data['savings_balance']:.2f} руб."
    )
    await safe_edit_message(query, text, reply_markup=main_menu_keyboard())

async def handle_balance(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    balance_data = get_total_balance(user_id)
    text = (
        f"💳 *Финансовый баланс*\n\n"
        f"💰 *Общий баланс:* {balance_data['current_balance']:.2f} руб.\n"
        f"├ Доходы всего: +{balance_data['total_income']:.2f} руб.\n"
        f"├ Расходы всего: -{balance_data['total_expense']:.2f} руб.\n"
        f"├ Вложено в накопления: -{balance_data['total_saved']:.2f} руб.\n"
        f"└ Снято с накоплений: +{balance_data['total_withdrawn']:.2f} руб.\n\n"
        f"🏦 *Накопительный счет:* {balance_data['savings_balance']:.2f} руб."
    )
    await safe_edit_message(query, text, reply_markup=main_menu_keyboard())

async def handle_help(query, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *Помощь по боту*\n\n"
        "Я помогаю вести учет финансов.\n\n"
        "💰 *Доходы* - добавляйте доходы по категориям\n"
        "💸 *Расходы* - добавляйте расходы по категориям\n"
        "🏦 *Накопления* - пополняйте и снимайте накопления\n"
        "📊 *Аналитика* - смотрите статистику за период\n"
        "📋 *Транзакции* - просмотр последних операций\n"
        "💳 *Баланс* - детальный баланс всех операций\n\n"
        "Просто нажимай кнопки и следуй инструкциями!"
    )
    await safe_edit_message(query, text, reply_markup=main_menu_keyboard())

async def handle_analytics_selection(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню аналитики"""
    await safe_edit_message(
        query,
        "📊 *Аналитика*\n\n"
        "Выберите период для отчета:",
        reply_markup=analytics_keyboard(),
        parse_mode='Markdown'
    )
    return True

# === СЛОВАРЬ ОБРАБОТЧИКОВ ===
MAIN_HANDLERS = {
    "income": handle_income_selection,
    "expense": handle_expense_selection,
    "back": handle_back,
    "balance": handle_balance,
    "help": handle_help,
    "analytics": handle_analytics_selection,
}

async def handle_main_button(query, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    if data in MAIN_HANDLERS:
        await MAIN_HANDLERS[data](query, context)
        return True
    return False