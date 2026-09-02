from datetime import datetime
from database import get_savings_balance, get_analytics
import matplotlib
matplotlib.use('Agg')  # Важно: без GUI backend
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np

def generate_monthly_report(user_id: int, year: int, month: int, analytics_data: dict):
    """
    Генерация отчета за конкретный месяц
    """
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Получаем текущий баланс
    current_balance = analytics_data.get('current_balance', 0)
    savings_balance = analytics_data.get('balance', 0)
    
    # Формируем отчет
    report = f"📊 *Отчет за {month_names[month-1]} {year}*\n"
    report += "═" * 30 + "\n\n"
    
    # Доходы и расходы
    total_income = analytics_data.get('total_income', 0)
    total_expense = analytics_data.get('total_expense', 0)
    
    report += f"💰 *Доходы:* {total_income:,.2f} руб.\n"
    report += f"📈 *Расходы:* {total_expense:,.2f} руб.\n\n"
    
    # Баланс за период
    period_balance = total_income - total_expense
    if period_balance >= 0:
        report += f"✅ *Баланс за месяц:* +{period_balance:,.2f} руб.\n"
    else:
        report += f"❌ *Баланс за месяц:* {period_balance:,.2f} руб.\n"
    
    report += f"💰 *Общий баланс:* {current_balance:,.2f} руб.\n"
    report += "\n" + "─" * 30 + "\n\n"
    
    # Расходы по категориям
    expense_by_category = analytics_data.get('expense_by_category', {})
    if expense_by_category:
        report += "📊 *Расходы по категориям:*\n"
        sorted_expenses = sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)
        
        total_expenses = analytics_data.get('total_expense', 0)
        for category, amount in sorted_expenses:
            percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
            bar_length = int(percentage / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            report += f"  {bar} {category}: {amount:,.2f} руб. ({percentage:.1f}%)\n"
        
        report += "\n" + "─" * 30 + "\n\n"
    else:
        report += "📊 *Расходы по категориям:*\n"
        report += "  Нет расходов за этот месяц.\n\n"
    
    # Доходы по категориям (если есть)
    income_by_category = analytics_data.get('income_by_category', {})
    if income_by_category:
        report += "💵 *Доходы по категориям:*\n"
        sorted_incomes = sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)
        
        total_income_amount = analytics_data.get('total_income', 0)
        for category, amount in sorted_incomes:
            percentage = (amount / total_income_amount * 100) if total_income_amount > 0 else 0
            bar_length = int(percentage / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            report += f"  {bar} {category}: {amount:,.2f} руб. ({percentage:.1f}%)\n"
        
        report += "\n" + "─" * 30 + "\n\n"
    
    # Накопительный счет
    report += "🏦 *Накопительный счет:*\n"
    report += f"  Текущий баланс: *{savings_balance:,.2f} руб.*\n"
    
    # Изменение на накопительном счете за месяц
    total_saved = analytics_data.get('total_saved', 0)
    total_withdrawn = analytics_data.get('total_withdrawn', 0)
    net_change = total_saved - total_withdrawn
    
    if net_change > 0:
        report += f"  📈 Изменение за месяц: +{net_change:,.2f} руб.\n"
        report += f"     (Пополнено: {total_saved:,.2f} руб. | Снято: {total_withdrawn:,.2f} руб.)\n"
    elif net_change < 0:
        report += f"  📉 Изменение за месяц: {net_change:,.2f} руб.\n"
        report += f"     (Пополнено: {total_saved:,.2f} руб. | Снято: {total_withdrawn:,.2f} руб.)\n"
    else:
        report += f"  ➖ Изменение за месяц: 0.00 руб.\n"
        if total_saved > 0 or total_withdrawn > 0:
            report += f"     (Пополнено: {total_saved:,.2f} руб. | Снято: {total_withdrawn:,.2f} руб.)\n"
        else:
            report += "     Нет операций с накоплениями за этот месяц.\n"
    
    report += "\n" + "═" * 30 + "\n"
    report += f"📅 Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    return report

def generate_analytics_report(user_id: int, analytics_data: dict, period: str):
    """Генерация текстового отчета по аналитике (для совместимости)"""
    if period == "Месяц":
        # Для совместимости с текущим месяцем
        current_month = datetime.now().month
        current_year = datetime.now().year
        return generate_monthly_report(user_id, current_year, current_month, analytics_data)
    else:
        # Годовая аналитика
        current_balance = analytics_data.get('current_balance', 0)
        savings_balance = analytics_data.get('balance', 0)
        
        report = f"📊 *Отчет за {period.lower()}*\n"
        report += "═" * 30 + "\n\n"
        
        total_income = analytics_data.get('total_income', 0)
        total_expense = analytics_data.get('total_expense', 0)
        
        report += f"💰 *Доходы:* {total_income:,.2f} руб.\n"
        report += f"📈 *Расходы:* {total_expense:,.2f} руб.\n\n"
        
        period_balance = total_income - total_expense
        if period_balance >= 0:
            report += f"✅ *Баланс за период:* +{period_balance:,.2f} руб.\n"
        else:
            report += f"❌ *Баланс за период:* {period_balance:,.2f} руб.\n"
        
        report += f"💰 *Общий баланс:* {current_balance:,.2f} руб.\n"
        report += "\n" + "─" * 30 + "\n\n"
        
        # ... остальной код для годовй аналитики (можно взять из предыдущей версии)
        # ...

        report += "\n" + "═" * 30 + "\n"
        report += f"📅 Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        return report


def generate_category_chart(data: dict, title: str, chart_type: str = 'pie') -> BytesIO:
    """
    Генерирует график расходов по категориям.
    
    Args:
        data: словарь {категория: сумма}
        title: заголовок графика
        chart_type: 'pie' (круговая) или 'bar' (столбчатая)
    
    Returns:
        BytesIO объект с изображением или None если нет данных
    """
    if not data or all(value == 0 for value in data.values()):
        return None
    
    # Сортируем по убыванию
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    categories = [item[0] for item in sorted_data]
    amounts = [item[1] for item in sorted_data]
    total = sum(amounts)
    
    # Настраиваем matplotlib
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['font.size'] = 10
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    if chart_type == 'pie':
        # Круговая диаграмма
        colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
        
        # Показываем только категории > 3%
        threshold = total * 0.03
        small_categories = [(cat, amt) for cat, amt in zip(categories, amounts) if amt < threshold]
        
        if small_categories:
            other_amount = sum(amt for _, amt in small_categories)
            categories = [cat for cat, amt in zip(categories, amounts) if amt >= threshold]
            amounts = [amt for amt in amounts if amt >= threshold]
            if other_amount > 0:
                categories.append('Другое')
                amounts.append(other_amount)
        
        wedges, texts, autotexts = ax.pie(
            amounts,
            labels=categories,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 9}
        )
        
        # Добавляем проценты только для крупных категорий
        for i, autotext in enumerate(autotexts):
            if amounts[i] / total < 0.05:
                autotext.set_visible(False)
    
    elif chart_type == 'bar':
        # Столбчатая диаграмма
        y_pos = np.arange(len(categories))
        bars = ax.barh(y_pos, amounts, color='steelblue', alpha=0.8)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories)
        ax.invert_yaxis()
        ax.set_xlabel('Сумма (руб.)')
        
        # Добавляем значения на бары
        for i, (bar, amount) in enumerate(zip(bars, amounts)):
            width = bar.get_width()
            percentage = (amount / total * 100) if total > 0 else 0
            ax.text(
                width, bar.get_y() + bar.get_height()/2,
                f' {amount:,.0f}₽ ({percentage:.1f}%)',
                ha='left', va='center', fontsize=9
            )
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    
    # Сохраняем в буфер
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()
    
    return buf