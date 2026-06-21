import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Стандартные категории
INCOME_CATEGORIES = ["Зарплата", "Фриланс", "Инвестиции", "Подарки", "Другое"]
EXPENSE_CATEGORIES = ["Продукты", "Транспорт", "Жилье", "Здоровье", "Образование", 
                      "Развлечения", "Одежда", "Связь", "Другое"]

# Настройки базы данных
DB_NAME = "finance.db"

# Настройки аналитики
ANALYTICS_PERIODS = ["Месяц", "Год"]