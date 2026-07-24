# handlers/saving.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_savings_balance
from keyboards import saving_actions_keyboard, main_menu_keyboard
from .utils import safe_edit_message

SAVING_HANDLERS = {}

async def handle_saving(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    balance = get_savings_balance(user_id)
    text = (
        f"🏦 *Управление накоплениями*\n\n"
        f"Текущий баланс: *{balance:.2f} руб.*\n\n"
        "Выберите действие:"
    )
    await safe_edit_message(query, text, reply_markup=saving_actions_keyboard(), parse_mode='Markdown')

async def handle_saving_add(query, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💰 Введите сумму пополнения накоплений (в рублях):\n\n"
        "Пример: 5000 или 10000.50\n\n"
        "❗ Описание не требуется.\n"
        "💡 Эти деньги будут списаны с основного баланса."
    )
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Отмена", callback_data="back")
        ]])
    )
    context.user_data['saving_action'] = 'add'

async def handle_saving_withdraw(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    balance = get_savings_balance(user_id)

    if balance <= 0:
        await safe_edit_message(
            query,
            "❌ У вас нет накоплений для снятия.",
            reply_markup=main_menu_keyboard()
        )
        return

    text = (
        f"💸 Введите сумму снятия с накоплений (в рублях):\n"
        f"Доступно: *{balance:.2f} руб.*\n\n"
        "Пример: 3000 или 1500.75\n\n"
        "❗ Описание не требуется.\n"
        "💡 Эти деньги будут зачислены на основной баланс."
    )
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Отмена", callback_data="back")
        ]]),
        parse_mode='Markdown'
    )
    context.user_data['saving_action'] = 'withdraw'

async def handle_saving_balance(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    balance = get_savings_balance(user_id)
    text = f"🏦 *Баланс накоплений*\n\nТекущий баланс: *{balance:.2f} руб.*"
    await safe_edit_message(query, text, reply_markup=main_menu_keyboard(), parse_mode='Markdown')

SAVING_HANDLERS = {
    "saving": handle_saving,
    "saving_add": handle_saving_add,
    "saving_withdraw": handle_saving_withdraw,
    "saving_balance": handle_saving_balance,
}

async def handle_saving_button(query, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    if data in SAVING_HANDLERS:
        await SAVING_HANDLERS[data](query, context)
        return True
    return False