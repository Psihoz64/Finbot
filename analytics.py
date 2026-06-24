from datetime import datetime
from database import get_savings_balance, get_analytics

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

def generate_category_chart(data: dict, title: str, color: str = '#3498db'):
    """Заглушка для совместимости"""
    return None