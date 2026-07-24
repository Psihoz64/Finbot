# handlers/utils.py
from telegram import Update
from telegram.error import BadRequest, NetworkError, TimedOut
import logging

logger = logging.getLogger(__name__)

async def safe_edit_message(query, text, reply_markup=None, parse_mode='Markdown'):
    """Безопасное редактирование с обработкой сетевых ошибок"""
    try:
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer("✅ Данные актуальны")
        else:
            logger.warning(f"BadRequest: {e}")
            await query.answer("⚠️ Ошибка редактирования")
    except (NetworkError, TimedOut) as e:
        logger.warning(f"Сетевая ошибка: {e}")
        await query.answer("⚠️ Проблемы с сетью. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")