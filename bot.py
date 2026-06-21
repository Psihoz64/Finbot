import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ConversationHandler, ContextTypes)

from config import BOT_TOKEN, INCOME_CATEGORIES, EXPENSE_CATEGORIES
from database import (init_db, add_transaction, get_transactions, 
                      get_savings_balance, get_analytics)
from keyboards import (main_menu_keyboard, categories_keyboard, 
                       analytics_keyboard, saving_actions_keyboard)
from states import States
from analytics import generate_category_chart, generate_analytics_report

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация БД
init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я твой финансовый помощник. Я помогу тебе:\n"
        "✅ Отслеживать доходы и расходы\n"
        "✅ Вести учет накоплений\n"
        "✅ Анализировать финансы\n\n"
        "Используй кнопки меню для навигации.",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "back":
        await query.message.edit_text(
            "📋 Главное меню:",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Доходы
    if data == "income":
        context.user_data['action'] = 'income'
        await query.message.edit_text(
            "💰 Выберите категорию дохода:",
            reply_markup=categories_keyboard(INCOME_CATEGORIES, 'income')
        )
        return
    
    # Расходы
    if data == "expense":
        context.user_data['action'] = 'expense'
        await query.message.edit_text(
            "💸 Выберите категорию расхода:",
            reply_markup=categories_keyboard(EXPENSE_CATEGORIES, 'expense')
        )
        return
    
    # Накопления
    if data == "saving":
        balance = get_savings_balance(user_id)
        await query.message.edit_text(
            f"🏦 *Управление накоплениями*\n\n"
            f"Текущий баланс: *{balance:.2f} руб.*\n\n"
            "Выберите действие:",
            reply_markup=saving_actions_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # Обработка пополнения накоплений
    if data == "saving_add":
        await query.message.edit_text(
            "💰 Введите сумму пополнения накоплений (в рублях):\n\n"
            "Пример: 5000 или 10000.50\n\n"
            "❗ Описание не требуется.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]])
        )
        context.user_data['saving_action'] = 'add'
        return
    
    # Обработка снятия с накоплений
    if data == "saving_withdraw":
        balance = get_savings_balance(user_id)
        if balance <= 0:
            await query.message.edit_text(
                "❌ У вас нет накоплений для снятия.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        await query.message.edit_text(
            f"💸 Введите сумму снятия с накоплений (в рублях):\n"
            f"Доступно: *{balance:.2f} руб.*\n\n"
            "Пример: 3000 или 1500.75\n\n"
            "❗ Описание не требуется.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Отмена", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
        context.user_data['saving_action'] = 'withdraw'
        return
    
    # Проверка баланса накоплений
    if data == "saving_balance":
        balance = get_savings_balance(user_id)
        await query.message.edit_text(
            f"🏦 *Баланс накоплений*\n\n"
            f"Текущий баланс: *{balance:.2f} руб.*",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # Аналитика
    if data == "analytics":
        await query.message.edit_text(
            "📊 Выберите период для аналитики:",
            reply_markup=analytics_keyboard()
        )
        return
    
    # Транзакции
    if data == "transactions":
        transactions = get_transactions(user_id, limit=10)
        if not transactions:
            await query.message.edit_text(
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
        
        await query.message.edit_text(
            text,
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # Помощь
    if data == "help":
        await query.message.edit_text(
            "ℹ️ *Помощь по боту*\n\n"
            "Я помогаю вести учет финансов.\n\n"
            "💰 *Доходы* - добавляйте доходы по категориям\n"
            "💸 *Расходы* - добавляйте расходы по категориям\n"
            "🏦 *Накопления* - пополняйте и снимайте накопления\n"
            "📊 *Аналитика* - смотрите статистику за период\n"
            "📋 *Транзакции* - просмотр последних операций\n\n"
            "Просто нажимай кнопки и следуй инструкциям!",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # Обработка выбора категории дохода
    if data.startswith('income_'):
        category = data.split('_', 1)[1]
        context.user_data['income_category'] = category
        await query.message.edit_text(
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
    
    # Обработка выбора категории расхода
    if data.startswith('expense_'):
        category = data.split('_', 1)[1]
        context.user_data['expense_category'] = category
        await query.message.edit_text(
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
    
    # Обработка выбора периода для аналитики
    if data.startswith('analytics_'):
        period = data.split('_', 1)[1]
        
        analytics_data = get_analytics(user_id, period)
        
        # Генерация текстового отчета
        report = generate_analytics_report(user_id, analytics_data, period)
        
        # Генерация диаграмм
        media_group = []
        
        # Диаграмма доходов
        if analytics_data['income_by_category']:
            chart = generate_category_chart(
                analytics_data['income_by_category'],
                f"Доходы по категориям ({period.lower()})",
                '#2ecc71'
            )
            if chart:
                media_group.append(('income_chart.png', chart))
        
        # Диаграмма расходов
        if analytics_data['expense_by_category']:
            chart = generate_category_chart(
                analytics_data['expense_by_category'],
                f"Расходы по категориям ({period.lower()})",
                '#e74c3c'
            )
            if chart:
                media_group.append(('expense_chart.png', chart))
        
        # Отправка отчета
        if media_group:
            # Отправляем текст
            await query.message.edit_text(
                report,
                reply_markup=main_menu_keyboard(),
                parse_mode='Markdown'
            )
            
            # Отправляем диаграммы
            for filename, chart in media_group:
                await query.message.reply_photo(
                    photo=chart,
                    caption=f"📊 {filename.replace('_chart.png', '').capitalize()}"
                )
                chart.close()
        else:
            await query.message.edit_text(
                report + "\n\nℹ️ Нет данных для построения диаграмм.",
                reply_markup=main_menu_keyboard(),
                parse_mode='Markdown'
            )
        return

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода (суммы транзакций)"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, есть ли ожидание ввода суммы
    saving_action = context.user_data.get('saving_action')
    income_category = context.user_data.get('income_category')
    expense_category = context.user_data.get('expense_category')
    
    # Обработка пополнения/снятия накоплений (БЕЗ ОПИСАНИЯ)
    if saving_action in ['add', 'withdraw']:
        try:
            # Парсим только число
            amount = float(text.strip())
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            if saving_action == 'add':
                add_transaction(user_id, 'saving', 'Накопления', amount, "", False)
                balance = get_savings_balance(user_id)
                await update.message.reply_text(
                    f"✅ Накопления пополнены на {amount:.2f} руб.\n"
                    f"Текущий баланс: {balance:.2f} руб.",
                    reply_markup=main_menu_keyboard()
                )
            else:  # withdraw
                balance = get_savings_balance(user_id)
                if amount > balance:
                    await update.message.reply_text(
                        f"❌ Недостаточно средств. Доступно: {balance:.2f} руб.",
                        reply_markup=main_menu_keyboard()
                    )
                    return
                
                add_transaction(user_id, 'saving', 'Накопления', amount, "", True)
                new_balance = get_savings_balance(user_id)
                await update.message.reply_text(
                    f"✅ Снято {amount:.2f} руб. с накоплений.\n"
                    f"Остаток: {new_balance:.2f} руб.",
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
    
    # Обработка дохода (с описанием через пробел)
    if income_category:
        try:
            # Разбиваем строку на части по пробелам
            parts = text.strip().split()
            
            # Первая часть - сумма
            amount = float(parts[0])
            
            # Остальные части - описание (собираем обратно через пробел)
            description = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            add_transaction(user_id, 'income', income_category, amount, description)
            await update.message.reply_text(
                f"✅ Доход добавлен:\n"
                f"Категория: {income_category}\n"
                f"Сумма: {amount:.2f} руб.\n"
                f"Описание: {description if description else 'Нет'}",
                reply_markup=main_menu_keyboard()
            )
            
            # Очищаем состояние
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
    
    # Обработка расхода (с описанием через пробел)
    if expense_category:
        try:
            # Разбиваем строку на части по пробелам
            parts = text.strip().split()
            
            # Первая часть - сумма
            amount = float(parts[0])
            
            # Остальные части - описание (собираем обратно через пробел)
            description = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть больше 0. Попробуйте снова.",
                    reply_markup=main_menu_keyboard()
                )
                return
            
            add_transaction(user_id, 'expense', expense_category, amount, description)
            await update.message.reply_text(
                f"✅ Расход добавлен:\n"
                f"Категория: {expense_category}\n"
                f"Сумма: {amount:.2f} руб.\n"
                f"Описание: {description if description else 'Нет'}",
                reply_markup=main_menu_keyboard()
            )
            
            # Очищаем состояние
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
        "📋 Просмотра транзакций",
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

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Запускаем бота
    print("🚀 Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()