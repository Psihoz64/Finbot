# handlers/analytics.py
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_savings_balance, get_analytics_for_month, check_month_has_data,
    get_categories, get_analytics
)
from keyboards import month_navigation_keyboard, main_menu_keyboard, analytics_keyboard
from .utils import safe_edit_message

logger = logging.getLogger(__name__)

from report_generator import generate_monthly_report, generate_analytics_report

async def handle_analytics_month(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    now = datetime.now()
    analytics_data = get_analytics_for_month(user_id, now.year, now.month)
    report = generate_monthly_report(user_id, now.year, now.month, analytics_data)
    await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')


async def handle_analytics_year(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    analytics_data = get_analytics(user_id, "Год")
    report = generate_analytics_report(user_id, analytics_data, "Год")
    await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')

# handlers/analytics.py
async def handle_month_select(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик клика на название месяца"""
    try:
        data = query.data
        logger.info(f"[handle_month_select] Данные: {data}")
        parts = data.split('_')
        if len(parts) != 4 or parts[0] != "month" or parts[1] != "select":
            logger.warning(f"[handle_month_select] Неверный формат: {data}")
            await safe_edit_message(query, "⚠️ Неверная команда", reply_markup=main_menu_keyboard())
            return True  # ← ВЕРНУЛИ TRUE, т.к. уже показали сообщение

        year = int(parts[2])
        month = int(parts[3])
        logger.info(f"[handle_month_select] Выбран месяц: {month}.{year}")

        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month

        user_id = query.from_user.id
        analytics_data = get_analytics_for_month(user_id, year, month)

        # Проверяем наличие данных
        if not analytics_data or not analytics_data.get('total_income') and not analytics_data.get('total_expense'):
            await safe_edit_message(query, "ℹ️ За этот месяц нет транзакций.", reply_markup=main_menu_keyboard())
            return True  # ← ВАЖНО: возвращаем True, чтобы сигналить, что запрос обработан

        report = generate_monthly_report(user_id, year, month, analytics_data)
        await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
        return True

    except Exception as e:
        logger.error(f"[handle_month_select] Ошибка: {e}", exc_info=True)
        await safe_edit_message(query, "❌ Ошибка при загрузке отчета.", reply_markup=main_menu_keyboard())
        return True  # ← И здесь тоже True, чтобы избежать зависания

async def handle_analytics_choose_month(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    now = datetime.now()

    context.user_data['analytics_year'] = now.year
    context.user_data['analytics_month'] = now.month

    has_prev = check_month_has_data(user_id, now.year, now.month - 1) if now.month > 1 else False

    keyboard = month_navigation_keyboard(now.year, now.month, has_prev=has_prev)
    await safe_edit_message(query, "📅 *Выберите месяц для аналитики*\n\nИспользуйте стрелки для навигации:", reply_markup=keyboard, parse_mode='Markdown')


async def handle_month_prev(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    year = context.user_data.get('analytics_year', datetime.now().year)
    month = context.user_data.get('analytics_month', datetime.now().month)

    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1

    context.user_data['analytics_year'] = year
    context.user_data['analytics_month'] = month

    has_prev = check_month_has_data(user_id, year, month - 1) if month > 1 else False
    has_next = check_month_has_data(user_id, year, month + 1) if month < 12 else False

    keyboard = month_navigation_keyboard(year, month, has_prev=has_prev)
    await safe_edit_message(query, f"📅 *{month}.{year}*", reply_markup=keyboard, parse_mode='Markdown')


async def handle_month_next(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    year = context.user_data.get('analytics_year', datetime.now().year)
    month = context.user_data.get('analytics_month', datetime.now().month)

    if month == 12:
        month = 1
        year += 1
    else:
        month += 1

    context.user_data['analytics_year'] = year
    context.user_data['analytics_month'] = month

    has_prev = check_month_has_data(user_id, year, month - 1) if month > 1 else False
    has_next = check_month_has_data(user_id, year, month + 1) if month < 12 else False

    keyboard = month_navigation_keyboard(year, month, has_prev=has_prev)
    await safe_edit_message(query, f"📅 *{month}.{year}*", reply_markup=keyboard, parse_mode='Markdown')


async def handle_month_show(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Показать отчет'"""
    try:
        data = query.data
        logger.info(f"[handle_month_show] Получены данные: {data}")
        parts = data.split('_')
        logger.info(f"[handle_month_show] Разделено на части: {parts}")
        
        if len(parts) != 4 or parts[0] != 'month' or parts[1] != 'show':
            logger.warning(f"[handle_month_show] Некорректный формат: {data}")
            await safe_edit_message(query, "⚠️ Некорректные данные кнопки.", reply_markup=main_menu_keyboard())
            return False
        
        try:
            year = int(parts[2])
            month = int(parts[3])
            logger.info(f"[handle_month_show] Распарсен год={year}, месяц={month}")
        except (ValueError, IndexError) as e:
            logger.error(f"[handle_month_show] Ошибка парсинга: {e}")
            await safe_edit_message(query, "❌ Ошибка при обработке даты.", reply_markup=main_menu_keyboard())
            return False
        
        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month
        
        user_id = query.from_user.id
        logger.info(f"[handle_month_show] Генерация отчета за {year}-{month:02d} для пользователя {user_id}")
        
        analytics_data = get_analytics_for_month(user_id, year, month)
        if not analytics_data or not analytics_data.get('total_income') and not analytics_data.get('total_expense'):
            logger.warning(f"[handle_month_show] Нет данных за {year}-{month:02d}")
            await safe_edit_message(query, "ℹ️ За этот месяц нет транзакций.", reply_markup=main_menu_keyboard())
            return False
        
        report = generate_monthly_report(user_id, year, month, analytics_data)
        
        logger.info(f"[handle_month_show] Отчет сгенерирован, отправка...")
        await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
        logger.info(f"[handle_month_show] Отчет отправлен успешно!")
        return True
    
    except Exception as e:
        logger.error(f"[handle_month_show] Неожиданная ошибка: {e}", exc_info=True)
        await safe_edit_message(query, "❌ Ошибка при загрузке отчета.", reply_markup=main_menu_keyboard())
        return False


async def handle_analytics_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню аналитики"""
    await safe_edit_message(
        query,
        "📊 *Аналитика*\n\n"
        "Выберите период для отчета:",
        reply_markup=analytics_keyboard(),
        parse_mode='Markdown'
    )

async def handle_noop(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пустой кнопки (заглушка)"""
    await query.answer("Выберите месяц с помощью стрелок")
    return True

# СЛОВАРЬ 
ANALYTICS_HANDLERS = {
    "analytics_месяц": handle_analytics_month,
    "analytics_год": handle_analytics_year,
    "analytics_choose_month": handle_analytics_choose_month,
    "month_prev": handle_month_prev,
    "month_next": handle_month_next,
    "analytics": handle_analytics_menu,  
    "noop": handle_noop,
    "month_select": handle_month_select,  
}


async def handle_analytics_button(query, context: ContextTypes.DEFAULT_TYPE):
    data = query.data
    logger.debug(f"handle_analytics_button: data={data}")

    # 1️⃣ Обработка клика на название месяца (НОВАЯ)
    if data.startswith("month_select_"):
        return await handle_month_select(query, context)  # ← достаточно просто return

    # 2️⃣ Ранее добавленная обработка кнопки "Показать отчет"
    elif data.startswith("month_show_"):
        result = await handle_month_show(query, context)
        return result  # и здесь достаточно return, т.к. он тоже всегда True

    # 3️⃣ Обработка остальных кнопок
    elif data in ANALYTICS_HANDLERS:
        await ANALYTICS_HANDLERS[data](query, context)
        return True
    
    return False