import matplotlib
matplotlib.use('Agg')
from datetime import datetime
from database import get_savings_balance

def generate_analytics_report(user_id: int, analytics_data: dict, period: str):
    """
    Генерация текстового отчета по аналитике
    
    Структура:
    - Доходы за месяц: сумма
    - Расходы за месяц: сумма
    - Категории расходов с суммами
    - Накопительный счет: баланс
    - Изменение на накопительном счете за месяц
    """
    
    # Получаем текущий баланс накоплений
    current_balance = get_savings_balance(user_id)
    
    # Формируем отчет
    report = f"📊 *Финансовый отчет за {period.lower()}*\n"
    report += "═" * 30 + "\n\n"
    
    # Доходы
    total_income = analytics_data.get('total_income', 0)
    report += f"💰 *Доходы:* {total_income:,.2f} руб.\n"
    report += f"📈 *Расходы:* {analytics_data.get('total_expense', 0):,.2f} руб.\n\n"
    
    # Баланс (доходы - расходы)
    balance = total_income - analytics_data.get('total_expense', 0)
    if balance >= 0:
        report += f"✅ *Баланс:* +{balance:,.2f} руб.\n"
    else:
        report += f"❌ *Баланс:* {balance:,.2f} руб.\n"
    report += "\n" + "─" * 30 + "\n\n"
    
    # Расходы по категориям (сортировка по убыванию)
    expense_by_category = analytics_data.get('expense_by_category', {})
    if expense_by_category:
        report += "📊 *Расходы по категориям:*\n"
        # Сортируем по сумме (от больших к меньшим)
        sorted_expenses = sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)
        
        total_expenses = analytics_data.get('total_expense', 0)
        for category, amount in sorted_expenses:
            # Вычисляем процент от общих расходов
            percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
            # Создаем визуальную шкалу
            bar_length = int(percentage / 5)  # Максимум 20 символов
            bar = "█" * bar_length + "░" * (20 - bar_length)
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
            report += f"  {bar} {category}: {amount:,.2f} руб. ({percentage:.1f}%)\n"
        
        report += "\n" + "─" * 30 + "\n\n"
    
    # Накопительный счет
    report += "🏦 *Накопительный счет:*\n"
    report += f"  Текущий баланс: *{current_balance:,.2f} руб.*\n"
    
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

# Функция для совместимости (если где-то используется)
def generate_category_chart(data: dict, title: str, color: str = '#3498db'):
    """Заглушка для совместимости (больше не используется)"""
    return None