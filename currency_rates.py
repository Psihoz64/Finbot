# currency_rates.py
import xml.etree.ElementTree as ET
import aiohttp
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

# Кэш курсов
_last_update = None      
_rates_cache = None  
_cbr_date = None

CACHE_DURATION = timedelta(hours=12)
TARGET_CURRENCIES = ["USD", "EUR", "CNY"]


def parse_cbr_xml(xml_text: str):
    """Парсит XML и извлекает курсы валют"""
    global _cbr_date
    rates = {}
    try:
        root = ET.fromstring(xml_text)
        logger.debug(f"🔍 parse_cbr_xml: XML корень = <{root.tag} ...>")
        
        val_curs_date_str = root.get('Date')
        logger.info(f"📅 parse_cbr_xml: Date атрибут = '{val_curs_date_str}'")
        
        if val_curs_date_str:
            _cbr_date = datetime.strptime(val_curs_date_str, "%d.%m.%Y")
            logger.info(f"✅ _cbr_date установлен: {_cbr_date.strftime('%d.%m.%Y')}")
        else:
            logger.warning("⚠️ Date атрибут отсутствует в XML — используем текущую дату")
            _cbr_date = datetime.now()

        for valute in root.findall('Valute'):
            char_code = valute.findtext('CharCode')
            value = valute.findtext('Value')
            
            if char_code in TARGET_CURRENCIES:
                if not value:
                    logger.warning(f"⚠️ Валюта {char_code} не содержит Value")
                    continue
                try:
                    value_float = float(value.replace(',', '.'))
                    rates[char_code] = value_float
                    logger.debug(f"📊 {char_code} = {value_float} RUB")
                except ValueError as e:
                    logger.error(f"❌ Ошибка парсинга значения {value} для {char_code}: {e}")
        
        logger.info(f"✅ parse_cbr_xml: получено {len(rates)} валют из {len(TARGET_CURRENCIES)} целевых")
        return rates
        
    except ET.ParseError as e:
        logger.error(f"❌ Ошибка парсинга XML ЦБ: {e}", exc_info=True)
        return {}


async def fetch_currency_rates():
    url = "https://www.cbr.ru/Scripts/XML_daily.asp"
    logger.info(f"🔄 Загрузка курсов валют с {url}")
    
    # === ДОБАВЛЯЕМ ТАЙМАУТЫ ДЛЯ ПРЕДОТВРАЩЕНИЯ ЗАВИСАНИЯ ===
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    xml_text = await response.text()
                    logger.debug(f"📊 XML response (первые 200 символов): {xml_text[:200]}...")
                    
                    rates = parse_cbr_xml(xml_text)
                    if rates:
                        logger.info(f"📊 ЦБ РФ: получено {len(rates)} валют")
                        return rates
                    else:
                        logger.warning("⚠️ ЦБ РФ: не удалось извлечь нужные валюты")
                        return None
                else:
                    logger.error(f"❌ ЦБ РФ: статус {response.status}, текст: {await response.text()}")
                    return None
        except asyncio.TimeoutError:
            logger.error("❌ Таймаут при запросе к ЦБ РФ (сайт недоступен)")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"❌ Сетевая ошибка при запросе к ЦБ РФ: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при запросе к ЦБ РФ: {e}", exc_info=True)
            return None


async def get_currency_rates() -> dict | None:
    global _last_update, _rates_cache, _cbr_date

    now = datetime.now()
    if _rates_cache and _last_update and (now - _last_update) < CACHE_DURATION:
        logger.info("📊 Курсы валют из кэша")
        return _rates_cache

    logger.info("🔄 Кэш истёк или отсутствует — обновление курсов...")
    rates = await fetch_currency_rates()

    if rates:
        _rates_cache = rates
        _last_update = now
        logger.info(f"✅ Курсы валют обновлены: {', '.join(rates.keys())}")
        return rates
    else:
        logger.error("❌ Не удалось загрузить курсы валют")
        return None


def format_currency_rate(code: str, rates: dict = None) -> str:
    if not rates or code not in rates:
        return f"{code}: ❌ Нет данных"
    rate = rates[code]
    return f"{rate:.2f} RUB"


def get_cbr_date() -> str | None:
    """Возвращает дату курсов от ЦБ в формате '24.07.2026'"""
    if _cbr_date:
        return _cbr_date.strftime('%d.%m.%Y')
    return None