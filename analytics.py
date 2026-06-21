from datetime import datetime
from database import get_savings_balance
from categories import clean_category_name

def generate_analytics_report(user_id: int, analytics_data: dict, period: str):
    """
    Генерация текстового отчета по аналитике с учетом общего баланса
    """
    # Получаем текущий баланс
    current_balance = analytics_data.get('current_balance', 0)
    savings_balance = analytics_data.get('balance', 0)
    
    # Формируем отчет
    report = f"📊 *Финансовый отчет за {period.lower()}*\n"
    report += "═" * 30 + "\n\n"
    
    # Доходы и расходы
    total_income = analytics_data.get('total_income', 0)
    total_expense = analytics_data.get('total_expense', 0)
    
    report += f"💰 *Доходы:* {total_income:,.2f} руб.\n"
    report += f"📈 *Расходы:* {total_expense:,.2f} руб.\n\n"
    
    # Баланс за период
    period_balance = total_income - total_expense
    if period_balance >= 0:
        report += f"✅ *Баланс за период:* +{period_balance:,.2f} руб.\n"
    else:
        report += f"❌ *Баланс за период:* {period_balance:,.2f} руб.\n"
    
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
            # Категория уже содержит эмодзи
            report += f"  {bar} {category}: {amount:,.2f} руб. ({percentage:.1f}%)\n"
        
        report += "\n" + "─" * 30 + "\n\n"
    else:
        report += "📊 *Расходы по категориям:*\n"
        report += "  Нет расходов за этот период.\n\n"
    
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
            # Категория уже содержит эмодзи
            report += f"  {bar} {category}: {amount:,.2f} руб. ({percentage:.1f}%)\n"
        
        report += "\n" + "─" * 30 + "\n\n"
    
    # Накопительный счет
    report += "🏦 *Накопительный счет:*\n"
    report += f"  Текущий баланс: *{savings_balance:,.2f} руб.*\n"
    
    # Изменение на накопительном счете за период
    total_saved = analytics_data.get('total_saved', 0)
    total_withdrawn = analytics_data.get('total_withdrawn', 0)
    net_change = total_saved - total_withdrawn
    
    if net_change > 0:
        report += f"  📈 Изменение за период: +{net_change:,.2f} руб.\n"
        report += f"     (Пополнено: {total_saved:,.2f} руб. | Снято: {total_withdrawn:,.2f} руб.)\n"
    elif net_change < 0:
        report += f"  📉 Изменение за период: {net_change:,.2f} руб.\n"
        report += f"     (Пополнено: {total_saved:,.2f} руб. | Снято: {total_withdrawn:,.2f} руб.)\n"
    else:
        report += f"  ➖ Изменение за период: 0.00 руб.\n"
        if total_saved > 0 or total_withdrawn > 0:
            report += f"     (Пополнено: {total_saved:,.2f} руб. | Снято: {total_withdrawn:,.2f} руб.)\n"
        else:
            report += "     Нет операций с накоплениями за этот период.\n"
    
    report += "\n" + "═" * 30 + "\n"
    report += f"📅 Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    return report

def generate_category_chart(data: dict, title: str, color: str = '#3498db'):
    """Заглушка для совместимости (больше не используется)"""
    return None