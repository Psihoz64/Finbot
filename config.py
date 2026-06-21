# config.py - ПОЛНАЯ ВЕРСИЯ С СОХРАНЕНИЕМ СТАРЫХ НАСТРОЕК
import os
from dotenv import load_dotenv
from typing import List

# Загружаем переменные из .env
load_dotenv()

class Config:
    # === ОСНОВНЫЕ НАСТРОЙКИ ===
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env файле!")
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///finance.db")
    
    # === АДМИНИСТРАТОРЫ ===
    ADMIN_IDS: List[int] = []
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
    
    # === НАСТРОЙКИ МОНИТОРИНГА ===
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))
    ALERT_TIMEOUT = int(os.getenv("ALERT_TIMEOUT", 600))
    
    # === ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ===
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # === НАСТРОЙКИ ДЛЯ АНАЛИТИКИ (были в старом config.py) ===
    ANALYTICS_PERIODS = {
        'day': '📅 За сегодня',
        'week': '📆 За неделю',
        'month': '📊 За месяц',
        'quarter': '📈 За квартал',
        'year': '📉 За год',
        'all': '📋 За всё время'
    }
    
    # === КАТЕГОРИИ ПО УМОЛЧАНИЮ (если нужны) ===
    DEFAULT_INCOME_CATEGORIES = ['Зарплата', 'Фриланс', 'Подарки', 'Инвестиции', 'Другое']
    DEFAULT_EXPENSE_CATEGORIES = ['Еда', 'Транспорт', 'Жильё', 'Развлечения', 'Здоровье', 'Одежда', 'Другое']

# Создаем экземпляр для удобства импорта
config = Config()

# === ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ (чтобы старый код работал) ===
BOT_TOKEN = config.BOT_TOKEN
ANALYTICS_PERIODS = config.ANALYTICS_PERIODS

# Если в старом коде использовались эти переменные
try:
    DEFAULT_INCOME_CATEGORIES = config.DEFAULT_INCOME_CATEGORIES
    DEFAULT_EXPENSE_CATEGORIES = config.DEFAULT_EXPENSE_CATEGORIES
except:
    pass