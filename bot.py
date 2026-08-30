# bot.py - ПОЛНАЯ ВЕРСИЯ С МОНИТОРИНГОМ И УЛУЧШЕННОЙ СЕТЬЮ

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
from telegram.request import HTTPXRequest
from telegram.ext import AIORateLimiter
from telegram.error import NetworkError, TimedOut

from config import BOT_TOKEN 
from database import (
    init_db, init_categories, add_transaction, get_transactions,
    get_savings_balance, get_analytics, get_total_balance, get_categories,
    check_month_has_data, get_analytics_for_month, get_db_connection
)
from keyboards import (
    main_menu_keyboard, categories_keyboard,
    analytics_keyboard, saving_actions_keyboard,
    month_navigation_keyboard)
from report_generator import generate_analytics_report, generate_monthly_report
from monitor import BotMonitor
from config import config

from tests.startup_checks import run_startup_checks

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация БД
init_db()

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ МОНИТОРИНГА ===
monitor = None
monitor_task = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    balance_data = get_total_balance(user_id)
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я — твой финансовый помощник.\n\n"
        f"💰 Баланс: {balance_data['current_balance']:.2f} руб.\n"
        f"🏦 Накопления: {balance_data['savings_balance']:.2f} руб."
    )
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ В главное меню", callback_data="back")
        ]]),
        parse_mode='Markdown'
    )
    pass
    

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    handled = False

    if data.startswith(('income_', 'expense_')):
        await handle_category_selection(query, context)
        handled = True

    if not handled:
        handled = await handle_main_button(query, context)

    if not handled:
        handled = await handle_saving_button(query, context)

    if not handled:
        handled = await handle_transactions_button(query, context)

    if not handled:
        handled = await handle_analytics_button(query, context)

    if not handled:
        if data == "currency_rates":
            handled = await handle_currency_rates(query, context)
        elif data == "currency_refresh":
            handled = await handle_currency_refresh(query, context)

    if not handled:
        await safe_edit_message(
            query,
            "❌ Неизвестная команда. Используйте кнопки меню.",
            reply_markup=main_menu_keyboard()
        )
        pass


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода (суммы транзакций)"""
    user_id = update.effective_user.id
    text = update.message.text
    
    saving_action = context.user_data.get('saving_action')
    income_category = context.user_data.get('income_category')
    expense_category = context.user_data.get('expense_category')
    
    # --- ОБРАБОТКА ВВОДА ДЛЯ ДОХОДОВ И РАСХОДОВ ---
    if income_category or expense_category:
        import re
        
        # Сначала пытаемся извлечь число и описание через regex
        match = re.match(r'([\d.]+)\s*(.*)', text.strip())
        
        if match:
            # Успешно нашли число и (возможно) описание
            amount_str = match.group(1)
            description = match.group(2).strip()
            
            try:
                amount = float(amount_str)
                if amount <= 0:
                    await update.message.reply_text(
                        "❌ Сумма должна быть больше 0. Попробуйте снова.",
                        reply_markup=main_menu_keyboard()
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "❌ Некорректный формат суммы. Введите число.\n"
                    "Пример: 100 или 5000.50",
                    reply_markup=main_menu_keyboard()
                )
                return
        else:
            # Regex не сработал - показываем ошибку
            await update.message.reply_text(
                "❌ Некорректный формат. Введите сумму (число) и описание через пробел.\n"
                "Пример: 5000 Зарплата\n"
                "Или просто число: 100",
                reply_markup=main_menu_keyboard()
            )
            return

        if income_category:
            tr_type = 'income'
            category_name = income_category
        else:
            tr_type = 'expense'
            category_name = expense_category

        add_transaction(user_id, tr_type, category_name, amount, description)
        
        balance_data = get_total_balance(user_id)
        
        if income_category:
            await update.message.reply_text(
                f"✅ Доход {amount:.2f} руб. добавлен!\n"
                f"💰 Баланс: {balance_data['current_balance']:.2f} руб.",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✅ Расход {amount:.2f} руб. добавлен!\n"
                f"💰 Баланс: {balance_data['current_balance']:.2f} руб.",
                reply_markup=main_menu_keyboard()
            )
        
        context.user_data.pop('income_category', None)
        context.user_data.pop('expense_category', None)
        return

    # --- ОБРАБОТКА НАКОПЛЕНИЙ ---
    if saving_action in ['add', 'withdraw', 'add_direct']:
        try:
            amount = float(text.strip())
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            if saving_action == 'add':
                total_balance_data = get_total_balance(user_id)
                if total_balance_data['current_balance'] < amount:
                    await update.message.reply_text(
                        f"❌ Недостаточно средств на основном балансе. "
                        f"Доступно: {total_balance_data['current_balance']:.2f} руб.",
                        reply_markup=main_menu_keyboard()
                    )
                    return

                add_transaction(user_id, 'saving', 'Пополнение накоплений', amount, "", False)
                
                balance = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ Накопления пополнены на {amount:.2f} руб.\n"
                    f"🏦 Баланс накоплений: {balance:.2f} руб.\n"
                    f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
                
            elif saving_action == 'add_direct':
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO savings_balance (user_id, balance)
                        VALUES (?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET 
                        balance = balance + excluded.balance
                    ''', (user_id, amount))
                    conn.commit()
                
                balance = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ На накопления начислено {amount:.2f} руб.\n"
                    f"🏦 Баланс накоплений: {balance:.2f} руб.\n"
                    f"💰 Основной баланс не изменился.",
                    reply_markup=main_menu_keyboard()
                )

            else:  # withdraw
                balance_before = get_savings_balance(user_id)
                
                if amount > balance_before:
                    await update.message.reply_text(
                        f"❌ Недостаточно средств. Доступно: {balance_before:.2f} руб.",
                        reply_markup=main_menu_keyboard()
                    )
                    return
                
                add_transaction(user_id, 'saving', 'Снятие с накоплений', amount, "", True)
                
                balance_after = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ Снято {amount:.2f} руб. с накоплений.\n"
                    f"🏦 Баланс накоплений: {balance_after:.2f} руб.\n"
                    f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
            
            context.user_data.pop('saving_action', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Некорректный формат. Введите число.\n"
                "Пример: 5000 или 10000",
                reply_markup=main_menu_keyboard()
            )
        return
    pass


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
    pass


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    context.user_data.clear()
    await update.message.reply_text(
        "✅ Действие отменено.",
        reply_markup=main_menu_keyboard()
    )
    pass


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
    pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок с фильтрацией сетевых сбоев"""
    error = context.error
    
    # 1. Игнорируем стандартные сетевые ошибки Telegram (часто возникают при Bad Gateway)
    if isinstance(error, (NetworkError, TimedOut)):
        logger.warning(f"⚠️ Сетевая ошибка Telegram API (игнорируем алерт): {error}")
        return
        
    # 2. Проверяем, не пробросился ли httpx.ReadError напрямую
    error_str = str(error)
    error_type = str(type(error).__name__)
    if "ReadError" in error_type or "ReadError" in error_str or "Bad Gateway" in error_str:
        logger.warning(f"⚠️ Сетевой сбой HTTPX (игнорируем алерт): {error}")
        return
    
    # 3. Логируем и отправляем админам только реальные баги кода
    logger.error(f"Критическая ошибка в боте: {error}", exc_info=error)
    
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"❌ Критическая ошибка в боте:\n```\n{str(error)[:500]}\n```",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить алерт админу {admin_id}: {e}")
            pass


async def start_monitoring(application: Application):
    """Запускает мониторинг в фоновом режиме"""
    global monitor, monitor_task
    
    logger.info("🔄 Инициализация мониторинга...")
    monitor = BotMonitor(application.bot)
    
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    logger.info("✅ Мониторинг запущен в фоновом режиме")
    pass


def main():
    """Запуск бота с улучшенными настройками сети"""
    init_categories()
     # === ШАГ 1: Инициализация БД ===
    print("🔧 Инициализация базы данных...")
    init_db()
    init_categories()
    
    # === ШАГ 2: Запуск самотестирования ===
    print("\n🧪 Запуск самотестирования...")
    
    # Запускаем асинхронные тесты
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        can_start = loop.run_until_complete(run_startup_checks())
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        can_start = False
    except Exception as e:
        print(f"\n❌ Критическая ошибка при тестировании: {e}")
        can_start = False
    
    if not can_start:
        print("\n🚫 Запуск бота отменён из-за критических ошибок.")
        print("Исправьте ошибки и попробуйте снова.")
        sys.exit(1)
    
    # === ШАГ 3: Настройка и запуск бота ===
    print("\n🚀 Запуск бота...")
    
    httpx_request = HTTPXRequest(
        connection_pool_size=10,  # Увеличенный пул соединений (по умолчанию 1)
        connect_timeout=15.0,     # Таймаут подключения
        read_timeout=15.0,        # Таймаут чтения (важно для long polling)
        write_timeout=15.0        # Таймаут записи
    )
    
    # === RATE LIMITER ДЛЯ ЗАЩИТЫ ОТ СПАМА API ===
    rate_limiter = AIORateLimiter()
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(httpx_request)
        .rate_limiter(rate_limiter)
        # .proxy(PROXY_URL)  # Включите, если сервер в регионе с блокировками
        .build()
    )
    
    # === РЕГИСТРИРУЕМ ОБРАБОТЧИКИ ===
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(CommandHandler("healthcheck", healthcheck))
    application.add_error_handler(error_handler)
    
    # === ЗАПУСК МОНИТОРИНГА ===
    loop = asyncio.get_event_loop()
    loop.call_later(2, lambda: asyncio.create_task(start_monitoring(application)))
    
    logger.info("🚀 Бот запущен!")
    
    # ВАЖНО: drop_pending_updates=True очистит очередь от старых сообщений
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import sys
    main()