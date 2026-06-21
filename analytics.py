from datetime import datetime
from database import get_savings_balance

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
            report += f"  {bar}