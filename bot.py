# bot.py - ПОЛНАЯ ВЕРСИЯ С МОНИТОРИНГОМ

from handlers.utils import safe_edit_message
from handlers.main import handle_main_button
from handlers.categories import handle_category_selection
from handlers.saving import handle_saving_button
from handlers.analytics import handle_analytics_button
from handlers.transactions import handle_transactions_button
from handlers.currency import handle_currency_rates, handle_currency_refresh
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes)

from config import BOT_TOKEN  # <--- ИЗМЕНЕНО: импортируем из config
from database import (
    init_db, init_categories, add_transaction, get_transactions,
    get_savings_balance, get_analytics, get_total_balance, get_categories,
    check_month_has_data, get_analytics_for_month)
from keyboards import (
    main_menu_keyboard, categories_keyboard,
    analytics_keyboard, saving_actions_keyboard,
    month_navigation_keyboard)
from report_generator import generate_analytics_report, generate_monthly_report
from monitor import BotMonitor  # <--- НОВЫЙ ИМПОРТ
from config import config  # <--- НОВЫЙ ИМПОРТ для настроек
from telegram.error import BadRequest

# Логигирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)  # ← ДОБАВИТЬ ЭТУ СТРОКУ


# Инициализация БД
init_db()

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ МОНИТОРИНГА (НОВЫЕ) ===
monitor = None
monitor_task = None

# ============================================
# ВСЕ ВАШИ СУЩЕСТВУЮЩИЕ ОБРАБОТЧИКИ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Получаем общий баланс
    balance_data = get_total_balance(user_id)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"💰 *Общий баланс:* {balance_data['current_balance']:.2f} руб.\n"
        f"🏦 *Накопления:* {balance_data['savings_balance']:.2f} руб.\n\n"
        "Я твой финансовый помощник. Я помогу тебе:\n"
        "✅ Отслеживать доходы и расходы\n"
        "✅ Вести учет накоплений\n"
        "✅ Анализировать финансы\n\n"
        "Используй кнопки меню для навигации.",
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    handled = False

    # 1️⃣ Категории (income, expense)
    if data.startswith(('income_', 'expense_')):
        await handle_category_selection(query, context)
        handled = True

    # 2️⃣ Основные кнопки (income, expense, back, balance, help, analytics)
    if not handled:
        handled = await handle_main_button(query, context)

    # 3️⃣ Накопления
    if not handled:
        handled = await handle_saving_button(query, context)

    # 4️⃣ Транзакции
    if not handled:
        handled = await handle_transactions_button(query, context)

    # 5️⃣ Аналитика
    if not handled:
        handled = await handle_analytics_button(query, context)

    # 6️⃣ Курсы валют
    if not handled:
        if data == "currency_rates":
            handled = await handle_currency_rates(query, context)
        elif data == "currency_refresh":
            handled = await handle_currency_refresh(query, context)

    # 🔒 Fallback
    if not handled:
        await safe_edit_message(
            query,
            "❌ Неизвестная команда. Используйте кнопки меню.",
            reply_markup=main_menu_keyboard()
        )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода (суммы транзакций)"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, есть ли ожидание ввода суммы
    saving_action = context.user_data.get('saving_action')
    income_category = context.user_data.get('income_category')
    expense_category = context.user_data.get('expense_category')
    
    # --- ОБРАБОТКА НАКОПЛЕНИЙ (БЕЗ ОПИСАНИЯ) ---
    if saving_action in ['add', 'withdraw']:
        try:
            amount = float(text.strip())
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            if saving_action == 'add':
                # Пополнение накоплений
                add_transaction(user_id, 'saving', 'Накопления', amount, "", False)
                balance = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ Накопления пополнены на {amount:.2f} руб.\n"
                    f"🏦 Баланс накоплений: {balance:.2f} руб.\n"
                    f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
            else:  # withdraw
                # Снятие с накоплений
                balance = get_savings_balance(user_id)
                if amount > balance:
                    await update.message.reply_text(
                        f"❌ Недостаточно средств. Доступно: {balance:.2f} руб.",
                        reply_markup=main_menu_keyboard()
                    )
                    return
                
                add_transaction(user_id, 'saving', 'Накопления', amount, "", True)
                new_balance = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ Снято {amount:.2f} руб. с накоплений.\n"
                    f"🏦 Баланс накоплений: {new_balance:.2f} руб.\n"
                    f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
            
            # Очищаем состояние
            context.user_data.pop('saving_action', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Некорректный формат. Введите число.\n"
                "Пример: 5000 или 10000",
                reply_markup=main_menu_keyboard()
            )
        return
    
    # --- ОБРАБОТКА ДОХОДА ---
    if income_category:
        try:
            parts = text.strip().split()
            amount = float(parts[0])
            description = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            add_transaction(user_id, 'income', income_category, amount, description)
            total_balance = get_total_balance(user_id)
            
            await update.message.reply_text(
                f"✅ Доход добавлен:\n"
                f"Категория: {income_category}\n"
                f"Сумма: {amount:.2f} руб.\n"
                f"Описание: {description if description else 'Нет'}\n\n"
                f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                reply_markup=main_menu_keyboard()
            )
            
            context.user_data.pop('income_category', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Некорректный формат. Введите сумму и описание через пробел.\n"
                "Пример: 50000 Зарплата за июнь\n"
                "Или просто: 50000",
                reply_markup=main_menu_keyboard()
            )
        except IndexError:
            await update.message.reply_text(
                "❌ Введите сумму.\n"
                "Пример: 50000 Зарплата за июнь",
                reply_markup=main_menu_keyboard()
            )
        return
    
    # --- ОБРАБОТКА РАСХОДА ---
    if expense_category:
        try:
            parts = text.strip().split()
            amount = float(parts[0])
            description = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            add_transaction(user_id, 'expense', expense_category, amount, description)
            total_balance = get_total_balance(user_id)
            
            await update.message.reply_text(
                f"✅ Расход добавлен:\n"
                f"Категория: {expense_category}\n"
                f"Сумма: {amount:.2f} руб.\n"
                f"Описание: {description if description else 'Нет'}\n\n"
                f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                reply_markup=main_menu_keyboard()
            )
            
            context.user_data.pop('expense_category', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Некорректный формат. Введите сумму и описание через пробел.\n"
                "Пример: 1500 Продукты в Ашане\n"
                "Или просто: 1500",
                reply_markup=main_menu_keyboard()
            )
        except IndexError:
            await update.message.reply_text(
                "❌ Введите сумму.\n"
                "Пример: 1500 Продукты в Ашане",
                reply_markup=main_menu_keyboard()
            )
        return
    
    # Если нет активного состояния
    await update.message.reply_text(
        "ℹ️ Используйте кнопки меню для взаимодействия.",
        reply_markup=main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "ℹ️ *Помощь по боту*\n\n"
        "Бот помогает вести учет финансов.\n\n"
        "📌 *Основные команды:*\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        "Используйте кнопки для:\n"
        "💰 Добавления доходов\n"
        "💸 Добавления расходов\n"
        "🏦 Управления накоплениями\n"
        "📊 Просмотра аналитики\n"
        "📋 Просмотра транзакций\n"
        "💳 Просмотра баланса",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    context.user_data.clear()
    await update.message.reply_text(
        "✅ Действие отменено.",
        reply_markup=main_menu_keyboard()
    )

# ============================================
# НОВЫЕ ОБРАБОТЧИКИ ДЛЯ МОНИТОРИНГА
# ============================================

async def healthcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки состояния бота (только для админов)"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    global monitor, monitor_task
    if not monitor:
        await update.message.reply_text("❌ Монитор не инициализирован.")
        return
    
    is_healthy = await monitor.ping()
    status_text = "✅ Бот работает" if is_healthy else "❌ Бот недоступен"
    
    last_ping_text = "Неизвестно"
    if monitor.last_ping:
        last_ping_text = monitor.last_ping.strftime('%d.%m.%Y %H:%M:%S')
    
    # Проверяем статус мониторинга
    monitor_status = "🟢 Активен" if monitor_task and not monitor_task.done() else "🔴 Остановлен"
    
    await update.message.reply_text(
        f"📊 **Статус мониторинга**\n\n"
        f"Состояние бота: {status_text}\n"
        f"Мониторинг: {monitor_status}\n"
        f"Последний пинг: {last_ping_text}\n"
        f"Администраторы: {', '.join(map(str, config.ADMIN_IDS))}\n\n"
        f"Интервал проверки: {config.CHECK_INTERVAL}с\n"
        f"Таймаут тревоги: {config.ALERT_TIMEOUT}с",
        parse_mode='Markdown'
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    # Уведомляем админов о критической ошибке
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"❌ Критическая ошибка в боте:\n```\n{str(context.error)[:500]}\n```",
                parse_mode='Markdown'
            )
        except:
            pass

# ============================================
# ФУНКЦИЯ ЗАПУСКА МОНИТОРИНГА
# ============================================

async def start_monitoring(application: Application):
    """Запускает мониторинг в фоновом режиме"""
    global monitor, monitor_task
    
    logger.info("🔄 Инициализация мониторинга...")
    monitor = BotMonitor(application.bot)
    
    # Запускаем мониторинг как фоновую задачу
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    logger.info("✅ Мониторинг запущен в фоновом режиме")

# ============================================
# ГЛАВНАЯ ФУНКЦИЯ (ОБНОВЛЕННАЯ)
# ============================================

def main():
    """Запуск бота"""
    # Инициализируем категории при первом запуске
    init_categories()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # === РЕГИСТРИРУЕМ ВСЕ ВАШИ СУЩЕСТВУЮЩИЕ ОБРАБОТЧИКИ ===
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # === НОВЫЕ ОБРАБОТЧИКИ ДЛЯ МОНИТОРИНГА ===
    application.add_handler(CommandHandler("healthcheck", healthcheck))
    application.add_error_handler(error_handler)
    
    # === ЗАПУСКАЕМ МОНИТОРИНГ В ФОНОВОМ РЕЖИМЕ ===
    # Используем asyncio для запуска мониторинга без блокировки основного цикла
    loop = asyncio.get_event_loop()
    loop.call_later(2, lambda: asyncio.create_task(start_monitoring(application)))
    
    # Запускаем бота
    logger.info("🚀 Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
