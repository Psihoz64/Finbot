import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройки базы данных
DB_NAME = "finance.db"

# Настройки аналитики
ANALYTICS_PERIODS = ["Месяц", "Год"]