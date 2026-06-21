import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
from telegram import InputFile
import tempfile
import os

def generate_category_chart(data: dict, title: str, color: str = '#3498db'):
    """Генерация круговой диаграммы по категориям"""
    if not data:
        return None
    
    plt.figure(figsize=(10, 8))
    
    categories = list(data.keys())
    values = list(data.values())
    
    # Если больше 5 категорий, остальные объединяем в "Другое"
    if len(categories) > 5:
        other_value = sum(values[5:])
        categories = categories[:5] + ["Другое"]
        values = values[:5] + [other_value]
    
    plt.pie(values, labels=categories, autopct='%1.1f%%', startangle=90,
            colors=[color, '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#95a5a6'])
    plt.title(title, fontsize=14, fontweight='bold')
    plt.axis('equal')
    
    # Сохраняем в буфер
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf

def generate_analytics_report(user_id: int, analytics_data: dict, period: str):
    """Генерация отчета по аналитике"""
    report = f"📊 *Аналитика за {period.lower()}*\n\n"
    report += f"💰 *Доходы:* {analytics_data['total_income']:.2f} руб.\n"
    report += f"💸 *Расходы:* {analytics_data['total_expense']:.2f} руб.\n"
    report += f"🏦 *Накопления:*\n"
    report += f"  • Пополнено: {analytics_data['total_saved']:.2f} руб.\n"
    report += f"  • Снято: {analytics_data['total_withdrawn']:.2f} руб.\n"
    report += f"  • Текущий баланс: {analytics_data['balance']:.2f} руб.\n\n"
    
    if analytics_data['total_income'] > 0:
        report += "*Доходы по категориям:*\n"
        for cat, amount in analytics_data['income_by_category'].items():
            report += f"  • {cat}: {amount:.2f} руб.\n"
    
    if analytics_data['total_expense'] > 0:
        report += "\n*Расходы по категориям:*\n"
        for cat, amount in analytics_data['expense_by_category'].items():
            report += f"  • {cat}: {amount:.2f} руб.\n"
    
    return report