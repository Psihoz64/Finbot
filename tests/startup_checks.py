# tests/startup_checks.py
"""
Система самотестирования бота при запуске.
Проверяет критические компоненты перед стартом.
"""

import logging
import asyncio
import sys
from datetime import datetime
from typing import List, Tuple, Optional

logger = logging.getLogger("startup_checks")


class TestResult:
    """Результат одного теста"""
    def __init__(self, name: str, passed: bool, message: str = "", 
                 duration: float = 0.0, critical: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.critical = critical
    
    def __str__(self):
        status = "✅" if self.passed else "❌"
        critical_mark = " [CRITICAL]" if self.critical and not self.passed else ""
        return f"{status} {self.name}{critical_mark} ({self.duration:.3f}s)"


class StartupChecker:
    """Менеджер проверок при запуске"""
    
    def __init__(self):
        self.results: List[TestResult] = []
    
    def add_result(self, name: str, passed: bool, message: str = "", 
                   duration: float = 0.0, critical: bool = True):
        result = TestResult(name, passed, message, duration, critical)
        self.results.append(result)
        logger.info(str(result))
    
    def run_sync_test(self, name: str, test_func, critical: bool = True):
        start = datetime.now()
        try:
            passed, message = test_func()
            duration = (datetime.now() - start).total_seconds()
            self.add_result(name, passed, message, duration, critical)
            return passed
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.add_result(name, False, f"Исключение: {str(e)}", duration, critical)
            return False
    
    async def run_async_test(self, name: str, test_func, critical: bool = True):
        start = datetime.now()
        try:
            passed, message = await test_func()
            duration = (datetime.now() - start).total_seconds()
            self.add_result(name, passed, message, duration, critical)
            return passed
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            self.add_result(name, False, f"Исключение: {str(e)}", duration, critical)
            return False
    
    def print_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        critical_failed = sum(1 for r in self.results if not r.passed and r.critical)
        
        print("\n" + "="*60)
        print("📊 РЕЗУЛЬТАТЫ САМОТЕСТИРОВАНИЯ")
        print("="*60)
        
        for result in self.results:
            print(str(result))
            if not result.passed and result.message:
                print(f"   ↳ {result.message}")
        
        print("\n" + "-"*60)
        print(f"Всего тестов: {total}")
        print(f"Пройдено: {passed} ✅")
        print(f"Провалено: {failed} ❌")
        
        if critical_failed > 0:
            print(f"\n🚨 КРИТИЧЕСКИХ ОШИБОК: {critical_failed}")
            return False
        elif failed > 0:
            print(f"\n⚠️ Предупреждений: {failed}")
            return True
        else:
            print("\n🎉 Все проверки пройдены успешно!")
            return True
    
    def all_critical_passed(self) -> bool:
        return all(r.passed for r in self.results if r.critical)


async def send_test_results_to_admins(checker: StartupChecker, bot_token: str):
    """Отправляет результаты тестов администраторам в Телеграм"""
    try:
        from telegram import Bot
        from config import config
        
        if not config.ADMIN_IDS:
            return
        
        bot = Bot(token=bot_token)
        
        total = len(checker.results)
        passed = sum(1 for r in checker.results if r.passed)
        failed = total - passed
        
        if failed == 0:
            status = "🎉 Все проверки пройдены!"
            emoji = "✅"
        elif any(not r.passed and r.critical for r in checker.results):
            status = "🚨 КРИТИЧЕСКИЕ ОШИБКИ!"
            emoji = "❌"
        else:
            status = "⚠️ Есть предупреждения"
            emoji = "⚠️"
        
        message = f"{emoji} *Результаты самотестирования бота*\n\n"
        message += f"Всего тестов: {total}\n"
        message += f"Пройдено: {passed}\n"
        message += f"Провалено: {failed}\n\n"
        
        failed_tests = [r for r in checker.results if not r.passed]
        if failed_tests:
            message += "*Ошибки:*\n"
            for result in failed_tests:
                critical_mark = " 🔴" if result.critical else ""
                message += f"• {result.name}{critical_mark}\n"
                if result.message:
                    message += f"  {result.message}\n"
        
        message += f"\n🕐 Время проверки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Не удалось отправить результаты админу {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка отправки результатов тестов: {e}")


async def run_startup_checks(send_to_telegram: bool = True) -> bool:
    """
    Запускает все проверки при старте.
    Возвращает True, если можно запускать бота.
    """
    checker = StartupChecker()
    
    print("\n🔍 Запуск самотестирования...")
    print("="*60)
    
    # === КРИТИЧЕСКИЕ ТЕСТЫ ===
    from tests.test_config import check_config
    checker.run_sync_test("Конфигурация", check_config, critical=True)
    
    from tests.test_database import check_database_structure
    checker.run_sync_test("Структура БД", check_database_structure, critical=True)
    
    from tests.test_database import check_categories
    checker.run_sync_test("Категории", check_categories, critical=True)
    
    from tests.test_database import check_crud_operations
    checker.run_sync_test("CRUD операции", check_crud_operations, critical=True)
    
    from tests.test_logic import check_balance_calculation
    checker.run_sync_test("Расчёт баланса", check_balance_calculation, critical=True)
    
    # === НЕКРИТИЧЕСКИЕ ТЕСТЫ ===
    from tests.test_config import check_telegram_api
    await checker.run_async_test("Telegram API", check_telegram_api, critical=False)
    
    from tests.test_logic import check_currency_rates
    await checker.run_async_test("Курсы валют", check_currency_rates, critical=False)
    
    from tests.test_logic import check_handlers_registered
    checker.run_sync_test("Обработчики", check_handlers_registered, critical=False)
    
    from tests.test_logic import check_keyboards
    checker.run_sync_test("Клавиатуры", check_keyboards, critical=False)
    
    # Выводим сводку
    can_start = checker.print_summary()
    
    # Отправляем результаты в Телеграм (если включено)
    if send_to_telegram:
        try:
            from config import BOT_TOKEN
            await send_test_results_to_admins(checker, BOT_TOKEN)
        except Exception as e:
            logger.warning(f"Не удалось отправить результаты в Телеграм: {e}")
    
    return can_start and checker.all_critical_passed()