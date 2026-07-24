# handlers/currency.py
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from keyboards import main_menu_keyboard
from .utils import safe_edit_message
from currency_rates import (
    TARGET_CURRENCIES,
    get_currency_rates,
    format_currency_rate,
    get_cbr_date,
)

logger = logging.getLogger(__name__)

CURRENCY_NAMES = {
    "USD": "Доллар США",
    "EUR": "Евро",
    "CNY": "Китайский юань"
}


async def handle_currency_rates(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Курсы валют'"""
    try:
        # ← СНАЧАЛА загружаем курсы → это обновит _cbr_date
        rates = await get_currency_rates()
        if not rates:
            raise Exception("Не удалось загрузить курсы валют")

        text = "💱 *Курс валют от ЦБ РФ*\n\n"

        # ← Теперь _cbr_date уже заполнена
        cbr_date = get_cbr_date()
        if cbr_date:
            text += f"📅 *Данные за:* {cbr_date}\n\n"
        else:
            text += "📅 *Данные за:* ⏳ Скачано, но дата неизвестна\n\n"

        for code, name in CURRENCY_NAMES.items():
            rate_str = format_currency_rate(code, rates)
            emoji = {"USD": "🇺🇸", "EUR": "🇪🇺", "CNY": "🇨🇳"}.get(code, "💱")
            text += f"{emoji} *{name}:* {rate_str}\n"

        text += "\nℹ️ Данные с официального сайта ЦБ РФ\n"

        await safe_edit_message(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Обновить курсы", callback_data="currency_refresh")],
                [InlineKeyboardButton("↩️ Назад", callback_data="back")]
            ]),
            parse_mode='Markdown'
        )
        return True

    except Exception as e:
        logger.error(f"Ошибка в handle_currency_rates: {e}", exc_info=True)
        await safe_edit_message(query, "❌ Ошибка при загрузке курсов валют.", reply_markup=main_menu_keyboard())
        return False


async def handle_currency_refresh(query, context: ContextTypes.DEFAULT_TYPE):
    """Обновить курсы вручную"""
    from currency_rates import _rates_cache, _last_update
    _rates_cache = None
    _last_update = None

    await handle_currency_rates(query, context)
    return True