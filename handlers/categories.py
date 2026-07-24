# handlers/categories.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_categories
from keyboards import categories_keyboard
from .utils import safe_edit_message

async def handle_category_selection(query, context: ContextTypes.DEFAULT_TYPE):
    data = query.data

    if data.startswith("income_"):
        category = data.split('_', 1)[1]
        context.user_data['income_category'] = category
        text = (
            f"💰 *Доход: {category}*\n\n"
            "Введите сумму и описание через пробел:\n"
            "Пример: 50000 Зарплата за июнь\n"
            "Или просто: 50000"
        )
        await safe_edit_message(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
    elif data.startswith("expense_"):
        category = data.split('_', 1)[1]
        context.user_data['expense_category'] = category
        text = (
            f"💸 *Расход: {category}*\n\n"
            "Введите сумму и описание через пробел:\n"
            "Пример: 1500 Продукты в Ашане\n"
            "Или просто: 1500"
        )
        await safe_edit_message(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )