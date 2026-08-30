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

# Настройка логирования для тестов
logger = logging.getLogger("startup_checks")


class TestResult:
    """Результат одного теста"""
    def __init__(self, name: str, passed: bool, message: str = "", 
                 duration: float = 0.0, critical: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.critical = critical  # Критичный тест блокирует запуск
    
    def __str__(self):
        status = "✅" if self.passed else "❌"
        critical_mark = " [CRITICAL]" if self.critical and not self.passed else ""
        return f"{status} {self.name}{critical_mark} ({self.duration:.3f}s)"


class StartupChecker:
    """Менеджер проверок при запуске"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
    
    def add_result(self, name: str, passed: bool, message: str = "", 
                   duration: float = 0.0, critical: bool = True):
        """Добавляет результат теста"""
        result = TestResult(name, passed, message, duration, critical)
        self.results.append(result)
        logger.info(str(result))
    
    def run_sync_test(self, name: str, test_func, critical: bool = True):
        """Запускает синхронный тест"""
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
        """Запускает асинхронный тест"""
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
        """Выводит сводку результатов"""
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
            print("❌ Запуск бота невозможен без исправления критических ошибок!")
            return False
        elif failed > 0:
            print(f"\n⚠️ Неправильных тестов: {failed}")
            print("⚠️ Бот будет запущен, но некоторые функции могут не работать.")
            return True
        else:
            print("\n🎉 Все проверки пройдены успешно!")
            return True
    
    def all_critical_passed(self) -> bool:
        """Проверяет, прошли ли все критические тесты"""
        return all(r.passed for r in self.results if r.critical)


async def run_startup_checks() -> bool:
    """
    Запускает все проверки при старте.
    Возвращает True, если можно запускать бота.
    """
    checker = StartupChecker()
    
    print("\n🔍 Запуск самотестирования...")
    print("="*60)
    
    # === КРИТИЧЕСКИЕ ТЕСТЫ (блокируют запуск) ===
    
    # 1. Проверка конфигурации
    from tests.test_config import check_config
    checker.run_sync_test("Конфигурация", check_config, critical=True)
    
    # 2. Проверка базы данных
    from tests.test_database import check_database_structure
    checker.run_sync_test("Структура БД", check_database_structure, critical=True)
    
    # 3. Проверка категорий
    from tests.test_database import check_categories
    checker.run_sync_test("Категории", check_categories, critical=True)
    
    # 4. Проверка CRUD операций
    from tests.test_database import check_crud_operations
    checker.run_sync_test("CRUD операции", check_crud_operations, critical=True)
    
    # 5. Проверка баланса
    from tests.test_logic import check_balance_calculation
    checker.run_sync_test("Расчёт баланса", check_balance_calculation, critical=True)
    
    # === НЕКРИТИЧЕСКИЕ ТЕСТЫ (не блокируют запуск) ===
    
    # 6. Проверка Telegram API
    from tests.test_config import check_telegram_api
    await checker.run_async_test("Telegram API", check_telegram_api, critical=False)
    
    # 7. Проверка курсов валют
    from tests.test_logic import check_currency_rates
    await checker.run_async_test("Курсы валют", check_currency_rates, critical=False)
    
    # 8. Проверка обработчиков
    from tests.test_logic import check_handlers_registered
    checker.run_sync_test("Обработчики", check_handlers_registered, critical=False)
    
    # 9. Проверка клавиатур
    from tests.test_logic import check_keyboards
    checker.run_sync_test("Клавиатуры", check_keyboards, critical=False)
    
    # Выводим сводку
    can_start = checker.print_summary()
    
    return can_start and checker.all_critical_passed()