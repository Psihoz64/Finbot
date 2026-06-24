# bot.py - ПОЛНАЯ ВЕРСИЯ С МОНИТОРИНГОМ
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
from analytics import generate_analytics_report
from monitor import BotMonitor  # <--- НОВЫЙ ИМПОРТ
from config import config  # <--- НОВЫЙ ИМПОРТ для настроек
from telegram.error import BadRequest

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)  # <--- ИЗМЕНЕНО: берем из config
)
logger = logging.getLogger(__name__)

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

async def safe_edit_message(query, text, reply_markup=None, parse_mode='Markdown'):
    """
    Безопасное редактирование сообщения с игнорированием ошибки 'Message is not modified'
    """
    try:
        await query.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer("✅ Данные актуальны")
        else:
            raise e

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    now = datetime.now() 
    
    # Возврат в главное меню
    if data == "back":
        balance_data = get_total_balance(user_id)
        await safe_edit_message(
            query,
            f"📋 *Главное меню*\n\n"
            f"💰 Баланс: {balance_data['current_balance']:.2f} руб.\n"
            f"🏦 Накопления: {balance_data['savings_balance']:.2f} руб.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # --- БАЛАНС ---
    if data == "balance":
        balance_data = get_total_balance(user_id)
        await safe_edit_message(
            query,
            f"💳 *Финансовый баланс*\n\n"
            f"💰 *Общий баланс:* {balance_data['current_balance']:,.2f} руб.\n"
            f"├ Доходы всего: +{balance_data['total_income']:,.2f} руб.\n"
            f"├ Расходы всего: -{balance_data['total_expense']:,.2f} руб.\n"
            f"├ Вложено в накопления: -{balance_data['total_saved']:,.2f} руб.\n"
            f"└ Снято с накоплений: +{balance_data['total_withdrawn']:,.2f} руб.\n\n"
            f"🏦 *Накопительный счет:* {balance_data['savings_balance']:,.2f} руб.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # --- ДОХОДЫ ---
    if data == "income":
        context.user_data['action'] = 'income'
        income_categories = get_categories('income')
        await safe_edit_message(
            query,
            "💰 Выберите категорию дохода:",
            reply_markup=categories_keyboard(income_categories, 'income')
        )
        return
    
    # --- РАСХОДЫ ---
    if data == "expense":
        context.user_data['action'] = 'expense'
        expense_categories = get_categories('expense')
        await safe_edit_message(
            query,
            "💸 Выберите категорию расхода:",
            reply_markup=categories_keyboard(expense_categories, 'expense')
        )
        return
    
    # --- НАКОПЛЕНИЯ ---
    if data == "saving":
        balance = get_savings_balance(user_id)
        await safe_edit_message(
            query,
            f"🏦 *Управление накоплениями*\n\n"
            f"Текущий баланс: *{balance:.2f} руб.*\n\n"
            "Выберите действие:",
            reply_markup=saving_actions_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if data == "saving_add":
        await safe_edit_message(
            query,
            "💰 Введите сумму пополнения накоплений (в рублях):\n\n"
            "Пример: 5000 или 10000.50\n\n"
            "❗ Описание не требуется.\n"
            "💡 Эти деньги будут списаны с основного баланса.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]])
        )
        context.user_data['saving_action'] = 'add'
        return
    
    if data == "saving_withdraw":
        balance = get_savings_balance(user_id)
        if balance <= 0:
            await safe_edit_message(
                query,
                "❌ У вас нет накоплений для снятия.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        await safe_edit_message(
            query,
            f"💸 Введите сумму снятия с накоплений (в рублях):\n"
            f"Доступно: *{balance:.2f} руб.*\n\n"
            "Пример: 3000 или 1500.75\n\n"
            "❗ Описание не требуется.\n"
            "💡 Эти деньги будут зачислены на основной баланс.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
        context.user_data['saving_action'] = 'withdraw'
        return
    
    if data == "saving_balance":
        balance = get_savings_balance(user_id)
        await safe_edit_message(
            query,
            f"🏦 *Баланс накоплений*\n\n"
            f"Текущий баланс: *{balance:.2f} руб.*",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # --- АНАЛИТИКА ---
    if data == "analytics":
        await safe_edit_message(
            query,
            "📊 *Аналитика*\n\n"
            "Выберите период для отчета:",
            reply_markup=analytics_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # --- ТРАНЗАКЦИИ ---
    if data == "transactions":
        transactions = get_transactions(user_id, limit=10)
        if not transactions:
            await safe_edit_message(
                query,
                "📋 У вас пока нет транзакций.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        text = "📋 *Последние 10 транзакций:*\n\n"
        for t in transactions[:10]:
            type_icon = "💰" if t['type'] == 'income' else "💸" if t['type'] == 'expense' else "🏦"
            desc = f" ({t['description']})" if t['description'] else ""
            date = datetime.fromisoformat(t['date']).strftime('%d.%m.%Y %H:%M')
            text += f"{type_icon} {t['category']}: {t['amount']:.2f} руб.{desc}\n"
            text += f"   📅 {date}\n"
        
        await safe_edit_message(
            query,
            text,
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # --- ПОМОЩЬ ---
    if data == "help":
        await safe_edit_message(
            query,
            "ℹ️ *Помощь по боту*\n\n"
            "Я помогаю вести учет финансов.\n\n"
            "💰 *Доходы* - добавляйте доходы по категориям\n"
            "💸 *Расходы* - добавляйте расходы по категориям\n"
            "🏦 *Накопления* - пополняйте и снимайте накопления\n"
            "📊 *Аналитика* - смотрите статистику за период\n"
            "📋 *Транзакции* - просмотр последних операций\n"
            "💳 *Баланс* - детальный баланс всех операций\n\n"
            "Просто нажимай кнопки и следуй инструкциям!",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # --- ВЫБОР МЕСЯЦА ДЛЯ АНАЛИТИКИ ---
    if data == "analytics_choose_month":
        context.user_data['analytics_year'] = now.year
        context.user_data['analytics_month'] = now.month
        
        await safe_edit_message(
            query,
            "📅 *Выберите месяц для аналитики*\n\n"
            "Используйте стрелки для навигации:",
            reply_markup=month_navigation_keyboard(now.year, now.month, has_prev=True),
            parse_mode='Markdown'
        )
        return
    
    # --- НАВИГАЦИЯ ПО МЕСЯЦАМ: НАЗАД ---
    if data == "month_prev":
        year = context.user_data.get('analytics_year', datetime.now().year)
        month = context.user_data.get('analytics_month', datetime.now().month)
        
        # Перемещаемся на месяц назад
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        
        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month
        
        # Проверяем наличие данных за предыдущий/следующий месяц
        has_prev = check_month_has_data(user_id, year, month - 1)
        has_next = check_month_has_data(user_id, year, month + 1)
        
        await safe_edit_message(
            query,
            f"📅 *{['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'][month-1]} {year}*\n\n"
            "Нажмите 'Показать отчет' для просмотра статистики.",
            reply_markup=month_navigation_keyboard(year, month, has_prev, has_next),
            parse_mode='Markdown'
        )
        return
    
    # --- НАВИГАЦИЯ ПО МЕСЯЦАМ: ВПЕРЕД ---
    if data == "month_next":
        year = context.user_data.get('analytics_year', datetime.now().year)
        month = context.user_data.get('analytics_month', datetime.now().month)
        
        # Проверяем, не пытаемся ли мы уйти в будущее
        if year > now.year or (year == now.year and month >= now.month):
            await query.answer("❌ Нельзя выбрать будущий месяц")
            return
        
        # Перемещаемся на месяц вперед
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        
        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month
        
        has_prev = check_month_has_data(user_id, year, month - 1)
        has_next = check_month_has_data(user_id, year, month + 1)
        
        await safe_edit_message(
            query,
            f"📅 *{['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'][month-1]} {year}*\n\n"
            "Нажмите 'Показать отчет' для просмотра статистики.",
            reply_markup=month_navigation_keyboard(year, month, has_prev, has_next),
            parse_mode='Markdown'
        )
        return
    
    # --- ПОКАЗ ОТЧЕТА ЗА ВЫБРАННЫЙ МЕСЯЦ ---
    if data.startswith('month_show_'):
        parts = data.split('_')
        year = int(parts[2])
        month = int(parts[3])
        
        # Получаем данные аналитики за период
        analytics_data = get_analytics_for_month(user_id, year, month)
        
        # Генерируем отчет
        report = generate_monthly_report(user_id, year, month, analytics_data)
        
        # Сохраняем выбранный месяц
        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month
        
        await safe_edit_message(
            query,
            report,
            reply_markup=month_navigation_keyboard(year, month),
            parse_mode='Markdown'
        )
        return
    
    # --- ТЕКУЩИЙ МЕСЯЦ ---
    if data == "analytics_месяц":
        analytics_data = get_analytics(user_id, "Месяц")
        report = generate_monthly_report(user_id, now.year, now.month, analytics_data)
        
        await safe_edit_message(
            query,
            report,
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # --- ТЕКУЩИЙ ГОД ---
    if data == "analytics_год":
        analytics_data = get_analytics(user_id, "Год")
        report = generate_analytics_report(user_id, analytics_data, "Год")
        
        await safe_edit_message(
            query,
            report,
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # --- ВЫБОР КАТЕГОРИИ ДОХОДА ---
    if data.startswith('income_'):
        category = data.split('_', 1)[1]
        context.user_data['income_category'] = category
        await safe_edit_message(
            query,
            f"💰 *Доход: {category}*\n\n"
            "Введите сумму и описание через пробел:\n"
            "Пример: 50000 Зарплата за июнь\n"
            "Или просто: 50000",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
        return
    
    # --- ВЫБОР КАТЕГОРИИ РАСХОДА ---
    if data.startswith('expense_'):
        category = data.split('_', 1)[1]
        context.user_data['expense_category'] = category
        await safe_edit_message(
            query,
            f"💸 *Расход: {category}*\n\n"
            "Введите сумму и описание через пробел:\n"
            "Пример: 1500 Продукты в Ашане\n"
            "Или просто: 1500",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
        return
    
    # --- ЕСЛИ НИ ОДНО УСЛОВИЕ НЕ СРАБОТАЛО ---
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