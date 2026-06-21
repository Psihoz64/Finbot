# monitor.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
import aiosqlite

from config import config

logger = logging.getLogger(__name__)

class BotMonitor:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.last_ping: Optional[datetime] = None
        self.is_healthy = True
        self.alert_sent = False
        self.check_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self):
        """Запускает фоновую проверку бота"""
        self.check_task = asyncio.create_task(self._monitor_loop())
        logger.info("Мониторинг бота запущен")
        
    async def stop_monitoring(self):
        """Останавливает мониторинг"""
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
            logger.info("Мониторинг бота остановлен")
    
    async def _monitor_loop(self):
        """Основной цикл проверки"""
        while True:
            try:
                await self._check_bot_health()
                await asyncio.sleep(config.CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def _check_bot_health(self):
        """Проверяет доступность бота"""
        try:
            # Проверяем, жив ли бот (get_me - легкий запрос)
            await self.bot.get_me()
            current_time = datetime.now()
            
            # Обновляем статус
            if not self.is_healthy:
                # Бот восстановился
                self.is_healthy = True
                self.alert_sent = False
                await self._notify_admins(
                    "✅ Бот восстановлен!",
                    "Бот снова доступен и отвечает на запросы."
                )
                logger.info("Бот восстановлен")
            
            self.last_ping = current_time
            
        except TelegramError as e:
            # Ошибка Telegram API
            logger.warning(f"Ошибка при проверке бота: {e}")
            await self._handle_health_failure()
        except Exception as e:
            # Другие ошибки
            logger.error(f"Критическая ошибка в мониторинге: {e}")
            await self._handle_health_failure()
    
    async def _handle_health_failure(self):
        """Обрабатывает сбой бота"""
        self.is_healthy = False
        
        # Проверяем, прошло ли достаточно времени для отправки алерта
        if self.last_ping and not self.alert_sent:
            time_since_last_ping = (datetime.now() - self.last_ping).total_seconds()
            if time_since_last_ping > config.ALERT_TIMEOUT:
                await self._send_alert()
                self.alert_sent = True
        elif not self.last_ping:
            # Первая проверка уже с ошибкой
            await self._send_alert()
            self.alert_sent = True
    
    async def _send_alert(self):
        """Отправляет предупреждение администраторам"""
        message = (
            "🚨 **СРОЧНО: Бот не отвечает!**\n\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"⏱ Бот недоступен более {config.ALERT_TIMEOUT // 60} минут\n\n"
            "🔍 Проверьте:\n"
            "• Логи бота\n"
            "• Доступность Telegram API\n"
            "• Сервер/хостинг\n"
            "• Интернет-соединение"
        )
        await self._notify_admins("⚠️ Бот недоступен!", message)
        logger.warning(f"Уведомление о недоступности отправлено админам: {config.ADMIN_IDS}")
    
    async def _notify_admins(self, title: str, message: str):
        """Отправляет уведомление всем администраторам"""
        if not config.ADMIN_IDS:
            logger.warning("Нет настроенных администраторов для уведомлений")
            return
        
        full_message = f"{title}\n\n{message}"
        
        for admin_id in config.ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=full_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Уведомление отправлено админу {admin_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    async def ping(self) -> bool:
        """Ручная проверка - можно вызвать из /healthcheck команды"""
        try:
            await self.bot.get_me()
            self.last_ping = datetime.now()
            self.is_healthy = True
            self.alert_sent = False
            return True
        except:
            return False