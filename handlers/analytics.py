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

from report_generator import (
    generate_monthly_report,
    generate_analytics_report,
    generate_category_chart
)


async def _send_expense_chart(context, user_id: int, analytics_data: dict, title: str):
    """Отправляет круговую диаграмму расходов, если есть данные"""
    try:
        expense_by_category = analytics_data.get('expense_by_category', {})
        if not expense_by_category:
            return
        chart_buf = generate_category_chart(expense_by_category, title, chart_type='pie')
        if chart_buf:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=chart_buf,
                caption=f"📊 {title}"
            )
    except Exception as e:
        logger.error(f"Не удалось отправить график: {e}")


async def handle_analytics_month(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    now = datetime.now()
    analytics_data = get_analytics_for_month(user_id, now.year, now.month)
    report = generate_monthly_report(user_id, now.year, now.month, analytics_data)
    await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
    await _send_expense_chart(context, user_id, analytics_data, f"Расходы за {now.strftime('%m.%Y')}")


async def handle_analytics_year(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    analytics_data = get_analytics(user_id, "Год")
    report = generate_analytics_report(user_id, analytics_data, "Год")
    await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
    await _send_expense_chart(context, user_id, analytics_data, f"Расходы за {datetime.now().year} год")


async def handle_month_select(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик клика на название месяца"""
    try:
        data = query.data
        parts = data.split('_')
        if len(parts) != 4 or parts[0] != "month" or parts[1] != "select":
            await safe_edit_message(query, "⚠️ Неверная команда", reply_markup=main_menu_keyboard())
            return True
        year = int(parts[2])
        month = int(parts[3])
        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month
        user_id = query.from_user.id
        analytics_data = get_analytics_for_month(user_id, year, month)
        if not analytics_data or not analytics_data.get('total_income') and not analytics_data.get('total_expense'):
            await safe_edit_message(query, "ℹ️ За этот месяц нет транзакций.", reply_markup=main_menu_keyboard())
            return True
        report = generate_monthly_report(user_id, year, month, analytics_data)
        await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
        await _send_expense_chart(context, user_id, analytics_data, f"Расходы за {month:02d}.{year}")
        return True
    except Exception as e:
        logger.error(f"[handle_month_select] Ошибка: {e}", exc_info=True)
        await safe_edit_message(query, "❌ Ошибка при загрузке отчета.", reply_markup=main_menu_keyboard())
        return True


async def handle_analytics_choose_month(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    now = datetime.now()
    context.user_data['analytics_year'] = now.year
    context.user_data['analytics_month'] = now.month
    has_prev = check_month_has_data(user_id, now.year, now.month - 1) if now.month > 1 else False
    keyboard = month_navigation_keyboard(now.year, now.month, has_prev=has_prev)
    await safe_edit_message(
        query,
        "📅 *Выберите месяц для аналитики*\n\nИспользуйте стрелки для навигации:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


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
    keyboard = month_navigation_keyboard(year, month, has_prev=has_prev)
    await safe_edit_message(query, f"📅 *{month}.{year}*", reply_markup=keyboard, parse_mode='Markdown')


async def handle_month_show(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Показать отчет'"""
    try:
        data = query.data
        parts = data.split('_')
        if len(parts) != 4 or parts[0] != 'month' or parts[1] != 'show':
            await safe_edit_message(query, "⚠️ Некорректные данные кнопки.", reply_markup=main_menu_keyboard())
            return False
        try:
            year = int(parts[2])
            month = int(parts[3])
        except (ValueError, IndexError) as e:
            logger.error(f"[handle_month_show] Ошибка парсинга: {e}")
            await safe_edit_message(query, "❌ Ошибка при обработке даты.", reply_markup=main_menu_keyboard())
            return False
        context.user_data['analytics_year'] = year
        context.user_data['analytics_month'] = month
        user_id = query.from_user.id
        analytics_data = get_analytics_for_month(user_id, year, month)
        if not analytics_data or not analytics_data.get('total_income') and not analytics_data.get('total_expense'):
            await safe_edit_message(query, "ℹ️ За этот месяц нет транзакций.", reply_markup=main_menu_keyboard())
            return False
        report = generate_monthly_report(user_id, year, month, analytics_data)
        await safe_edit_message(query, report, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
        await _send_expense_chart(context, user_id, analytics_data, f"Расходы за {month:02d}.{year}")
        return True
    except Exception as e:
        logger.error(f"[handle_month_show] Неожиданная ошибка: {e}", exc_info=True)
        await safe_edit_message(query, "❌ Ошибка при загрузке отчета.", reply_markup=main_menu_keyboard())
        return False


async def handle_analytics_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню аналитики"""
    await safe_edit_message(
        query,
        "📊 *Аналитика*\n\nВыберите период для отчета:",
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

    if data.startswith("month_select_"):
        return await handle_month_select(query, context)
    elif data.startswith("month_show_"):
        return await handle_month_show(query, context)
    elif data in ANALYTICS_HANDLERS:
        await ANALYTICS_HANDLERS[data](query, context)
        return True

    return False