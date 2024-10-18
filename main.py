import asyncio
import os
import json
import base64
import logging
import sys

from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.types import InputFile
from configparser import ConfigParser

from helper import number_to_emoji

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Здесь можно установить уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sys.stdout.reconfigure(encoding='utf-8')

# Load configuration
config = ConfigParser()
config.read('config.ini')

if not config.has_section('Settings') or not config.has_option('Settings', 'MAIN_FOLDER'):
    logging.error("Секция [Settings] или параметр MAIN_FOLDER не найдены в config.ini")
    raise ValueError("Настройки MAIN_FOLDER не найдены в config.ini")

MAIN_FOLDER = config.get('Settings', 'MAIN_FOLDER')

# Проверка наличия секции 'Bot' и параметра 'API_TOKEN'
if not config.has_section('Bot') or not config.has_option('Bot', 'API_TOKEN'):
    logging.error("Секция [Bot] или параметр API_TOKEN не найдены в config.ini")
    raise ValueError("Настройки API_TOKEN не найдены в config.ini")

API_TOKEN = config.get('Bot', 'API_TOKEN')

# Initialize bot and dispatcher
bot = Bot(token="7710502164:AAFwCa1oYvmKqMlzd6kdxm-xaLDKojJR0dI")
dp = Dispatcher(bot)



# Function to send messages
async def send_daily_reports():
    try:
        ids_file = os.path.join(MAIN_FOLDER, 'ids', 'ids.txt')
        users_file = os.path.join(os.getcwd(), 'users.json')

        # Load user mappings
        if not os.path.exists(users_file):
            print(f"Users mapping file not found at {users_file}")
            return

        with open(users_file, 'r', encoding='utf-8') as uf:
            users_mapping = json.load(uf)  # This should be a dict {establishment_id: [user_id, ...]}

        # Read establishment IDs
        if not os.path.exists(ids_file):
            print(f"IDs file not found at {ids_file}")
            return

        with open(ids_file, 'r', encoding='utf-8') as f:
            establishment_ids = [line.strip() for line in f if line.strip()]

        for establishment_id in establishment_ids:
            establishment_folder = os.path.join(MAIN_FOLDER, establishment_id)
            if not os.path.exists(establishment_folder):
                print(f"Folder for establishment {establishment_id} not found.")
                continue

            # Get the users to send messages to for this establishment
            user_ids = users_mapping.get(establishment_id, [])
            if not user_ids:
                print(f"No users to send messages to for establishment {establishment_id}")
                continue

            # Read stat.json
            stat_file = os.path.join(establishment_folder, 'stat.json')
            if not os.path.exists(stat_file):
                print(f"stat.json not found for {establishment_id}")
                continue

            with open(stat_file, 'r', encoding='utf-8') as sf:
                stat_data = json.load(sf)

            org_rate = stat_data.get('org_rate', 'N/A')
            org_name = stat_data.get('org_name', 'N/A')
            org_feedback = stat_data.get('org_feedback', 'No data')
            screenshot_base64 = stat_data.get('SCREENSHOT_PEREHOD_BY_YEAR', '')

           # Read concurrents.txt
            concurrents_file = os.path.join(establishment_folder, 'concurents.txt')
            if not os.path.exists(concurrents_file):
                print(f"concurents.txt не найден для {establishment_id}")
                concurrents = []
            else:
                with open(concurrents_file, 'r', encoding='utf-8') as cf:
                    concurrents_lines = cf.read().splitlines()

                concurrents = []
                for cline in concurrents_lines:
                    cparts = cline.strip().split(':')
                    if len(cparts) != 4:
                        print(f"Неверная строка в concurents.txt: {cline}")
                        continue
                    position, share, name, is_own = cparts
                    concurrents.append({
                        'position': position,
                        'share': share.strip(),
                        'name': name.strip(),
                        'is_own': is_own.strip() == 'True'
                    })

            # Build the message
            message_lines = []
            message_lines.append(f"📍 {org_name} 📍\n")
            today_str = datetime.now().strftime("📅 %d.%m.%Y\n")
            message_lines.append(today_str)

            rating_emoji = number_to_emoji(org_rate)
            message_lines.append(f"⭐️ Рейтинг: {rating_emoji}")
            message_lines.append(f"\n📝 Отзывы: {org_feedback}\n")

            message_lines.append("👨‍👩‍👦‍👦 Конкуренты:")
            total_concurrents = len(concurrents)
            for idx, c in enumerate(concurrents, start=1):
                is_last = idx == total_concurrents
                prefix = '└──' if is_last else '├──'
                circle = '🟢' if c['is_own'] else '🔴'
                line = f"{prefix} {circle} {c['name']} ({c['share']})"
                message_lines.append(line)

            message_text = '\n'.join(message_lines)

            # Send the message to each user
            for user_id in user_ids:
                try:
                    # Send the text message
                    await bot.send_message(chat_id=int(user_id), text=message_text)

                    # If there is an image, send it
                    if screenshot_base64:
                        image_data = base64.b64decode(screenshot_base64)
                        photo = InputFile.from_buffer(image_data, filename='screenshot.png')
                        await bot.send_photo(chat_id=int(user_id), photo=photo)
                except BotBlocked:
                    print(f"Бот заблокирован пользователем {user_id}")
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    except Exception as err:
        print(f"Error: {err}")


# Schedule the daily task
# Планирование ежедневной задачи
async def scheduler():
    while True:
        now = datetime.now()
        next_run = now.replace(hour=16, minute=52, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logging.info(f"Следующая отправка отчетов запланирована на {next_run} (через {wait_seconds} секунд)")
        await asyncio.sleep(wait_seconds)
        await send_daily_reports()

# Start polling and scheduler
if __name__ == '__main__':
    logging.info(f"MAIN_FOLDER установлен на: {MAIN_FOLDER}")

    loop = asyncio.get_event_loop()
    loop.create_task(scheduler())
    executor.start_polling(dp, skip_updates=True)