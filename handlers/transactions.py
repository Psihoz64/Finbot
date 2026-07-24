# handlers/transactions.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_transactions
from keyboards import main_menu_keyboard
from .utils import safe_edit_message
from datetime import datetime

async def handle_transactions(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    transactions = get_transactions(user_id, limit=10)

    if not transactions:
        await safe_edit_message(
            query,
            "📋 У вас пока нет транзакций.",
            reply_markup=main_menu_keyboard()
        )
        return

    text = "📋 *Последние 10 транзакций*\n\n"
    for t in transactions[:10]:
        icon = "💰" if t['type'] == 'income' else "💸" if t['type'] == 'expense' else "🏦"
        desc = f" ({t['description']})" if t['description'] else ""
        date = datetime.fromisoformat(t['date']).strftime('%d.%m.%Y %H:%M')
        text += f"{icon} {t['category']}: {t['amount']:.2f} руб.{desc}\n"
        text += f"   📅 {date}\n"

    await safe_edit_message(
        query,
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )

TRANSACTIONS_HANDLERS = {
    "transactions": handle_transactions,
}

async def handle_transactions_button(query, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    if data in TRANSACTIONS_HANDLERS:
        await TRANSACTIONS_HANDLERS[data](query, context)
        return True
    return False