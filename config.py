# config.py
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env файле!")
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///finance.db")
    
    ADMIN_IDS: List[int] = []
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
    
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))
    ALERT_TIMEOUT = int(os.getenv("ALERT_TIMEOUT", 600))
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()
BOT_TOKEN = config.BOT_TOKEN  # Для обратной совместимости