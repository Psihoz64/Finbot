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

from config import BOT_TOKEN 
from database import (
    init_db, init_categories, add_transaction, get_transactions,
    get_savings_balance, get_analytics, get_total_balance, get_categories,
    check_month_has_data, get_analytics_for_month, get_db_connection # <-- ДОБАВИТЬ ЭТОТ ИМПОРТ
)
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



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Получаем общий баланс
    balance_data = get_total_balance(user_id)
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я — твой финансовый помощник.\n\n"
        f"💰 Баланс: {balance_data['current_balance']:.2f} руб.\n"
        f"🏦 Накопления: {balance_data['savings_balance']:.2f} руб."
    )
    
    # Отправляем приветственное сообщение с кнопкой "Начать работу", которая будет вести в главное меню
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ В главное меню", callback_data="back") # Используем "back", так как handle_back формирует главное меню
        ]]),
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
    
    # --- ОБРАБОТКА ВВОДА ДЛЯ ДОХОДОВ И РАСХОДОВ ---
    if income_category or expense_category:
        try:
            amount = float(text.strip())
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return

            # Определяем тип транзакции и название категории
            if income_category:
                tr_type = 'income'
                category_name = income_category # <-- ИСПРАВЛЕНО: используем переменную категории
            else:
                tr_type = 'expense'
                category_name = expense_category # <-- ИСПРАВЛЕНО: используем переменную категории

            # Добавляем транзакцию (описание берем из текста, если пользователь ввел сумму и описание)
            # В текущей логике категорий, пользователь вводит "Сумма Описание"
            # Но в handlers/categories.py мы отправляем текст "Введите сумму и описание через пробел"
            # Однако, здесь мы можем просто использовать всю строку как описание, если она не чистое число.
            # Но проще всего: первая часть строки - сумма, остальное - описание.
            
            # Разбираем ввод: "1000 Зарплата" -> amount=1000, desc="Зарплата"
            # Или "1000" -> amount=1000, desc=""
            
            # Уже извлекли amount из float(text), но теперь нужно пересобрать для desc
            # Так как text.strip() был использован для float, нам нужно найти описание.
            # Простой способ: найти первое пробел после цифры.
            import re
            match = re.match(r'([\d.]+)\s+(.*)', text)
            if match:
                description = match.group(2).strip()
            else:
                description = ""

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
            
            # Очищаем состояние
            context.user_data.pop('income_category', None)
            context.user_data.pop('expense_category', None)

        except ValueError:
            await update.message.reply_text(
                "❌ Некорректный формат. Введите сумму (число) и описание через пробел.\n"
                "Пример: 5000 Зарплата",
                reply_markup=main_menu_keyboard()
            )
        return

    # --- ОБРАБОТКА НАКОПЛЕНИЙ (БЕЗ ОПИСАНИЯ) ---
    if saving_action in ['add', 'withdraw', 'add_direct']:
        try:
            amount = float(text.strip())
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            # 1. Пополнение с основного баланса
            if saving_action == 'add':
                total_balance_data = get_total_balance(user_id)
                if total_balance_data['current_balance'] < amount:
                    await update.message.reply_text(
                        f"❌ Недостаточно средств на основном балансе. "
                        f"Доступно: {total_balance_data['current_balance']:.2f} руб.",
                        reply_markup=main_menu_keyboard()
                    )
                    return

                # Создаем транзакцию: тип 'saving', without withdrawal flag
                add_transaction(user_id, 'saving', 'Пополнение накоплений', amount, "", False)
                
                balance = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ Накопления пополнены на {amount:.2f} руб.\n"
                    f"🏦 Баланс накоплений: {balance:.2f} руб.\n"
                    f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
                
            # 2. Пополнение извне (проценты, дивиденды) - не влияет на общий баланс напрямую через формулу
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

            # 3. Снятие с накоплений
            else:  # withdraw
                balance_before = get_savings_balance(user_id)
                
                if amount > balance_before:
                    await update.message.reply_text(
                        f"❌ Недостаточно средств. Доступно: {balance_before:.2f} руб.",
                        reply_markup=main_menu_keyboard()
                    )
                    return
                
                # Создаем транзакцию: тип 'saving', with withdrawal flag
                add_transaction(user_id, 'saving', 'Снятие с накоплений', amount, "", True)
                
                balance_after = get_savings_balance(user_id)
                total_balance = get_total_balance(user_id)
                
                await update.message.reply_text(
                    f"✅ Снято {amount:.2f} руб. с накоплений.\n"
                    f"🏦 Баланс накоплений: {balance_after:.2f} руб.\n"
                    f"💰 Общий баланс: {total_balance['current_balance']:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
            
            # Очищаем состояние после успешной операции
            context.user_data.pop('saving_action', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Некорректный формат. Введите число.\n"
                "Пример: 5000 или 10000",
                reply_markup=main_menu_keyboard()
            )
        # Важно: return здесь завершает обработку этого сообщения
        return

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
