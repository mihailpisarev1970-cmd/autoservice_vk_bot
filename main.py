import sys
import asyncio

# Исправление таймаута семафора и проблем с SSL в Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from vkbottle import Bot
from config import settings
from handlers import labeler

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.VK_TOKEN, labeler=labeler)

# Передаем API и диспенсер состояний бота в обработчики
labeler.custom_rules["api"] = bot.api
labeler.custom_rules["state_dispenser"] = bot.state_dispenser

if __name__ == "__main__":
    print("🚀 Бот автосервиса для ВКонтакте запущен!")
    bot.run_forever()