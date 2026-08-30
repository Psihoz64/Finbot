# tests/test_config.py
"""Тесты конфигурации бота"""

import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def check_config() -> Tuple[bool, str]:
    """Проверяет наличие и корректность конфигурации"""
    errors = []
    
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        errors.append("Файл .env не найден")
    
    # Проверяем токен
    try:
        from config import BOT_TOKEN
        if not BOT_TOKEN:
            errors.append("BOT_TOKEN пустой")
        elif len(BOT_TOKEN) < 30:
            errors.append("BOT_TOKEN слишком короткий (неверный формат)")
        elif ':' not in BOT_TOKEN:
            errors.append("BOT_TOKEN не содержит ':' (неверный формат)")
    except ImportError:
        errors.append("Не удалось импортировать BOT_TOKEN из config.py")
    except Exception as e:
        errors.append(f"Ошибка при чтении BOT_TOKEN: {str(e)}")
    
    # Проверяем ADMIN_IDS
    try:
        from config import config
        if not hasattr(config, 'ADMIN_IDS'):
            errors.append("ADMIN_IDS не определён в config")
        elif not config.ADMIN_IDS:
            errors.append("ADMIN_IDS пустой (некому отправлять алерты)")
        elif not isinstance(config.ADMIN_IDS, (list, tuple)):
            errors.append("ADMIN_IDS должен быть списком")
    except ImportError:
        errors.append("Не удалось импортировать config")
    except Exception as e:
        errors.append(f"Ошибка при чтении ADMIN_IDS: {str(e)}")
    
    # Проверяем параметры мониторинга
    try:
        from config import config
        if not hasattr(config, 'CHECK_INTERVAL'):
            errors.append("CHECK_INTERVAL не определён")
        elif config.CHECK_INTERVAL <= 0:
            errors.append("CHECK_INTERVAL должен быть > 0")
        
        if not hasattr(config, 'ALERT_TIMEOUT'):
            errors.append("ALERT_TIMEOUT не определён")
        elif config.ALERT_TIMEOUT <= 0:
            errors.append("ALERT_TIMEOUT должен быть > 0")
    except Exception as e:
        errors.append(f"Ошибка при чтении параметров мониторинга: {str(e)}")
    
    if errors:
        return False, "; ".join(errors)
    return True, "Конфигурация корректна"


async def check_telegram_api() -> Tuple[bool, str]:
    """Проверяет доступность Telegram API"""
    try:
        from config import BOT_TOKEN
        from telegram import Bot
        
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        
        return True, f"Бот @{me.username} доступен"
        
    except ImportError as e:
        return False, f"Ошибка импорта: {str(e)}"
    except Exception as e:
        error_msg = str(e)
        if "Unauthorized" in error_msg:
            return False, "Неверный токен бота"
        elif "ConnectError" in error_msg or "connection" in error_msg.lower():
            return False, "Нет соединения с Telegram API (проверьте интернет/прокси)"
        else:
            return False, f"Ошибка подключения: {error_msg}"