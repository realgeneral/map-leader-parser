import asyncio
import os
import json
import base64
import logging
import sys
import shutil

from io import BytesIO 
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import BotBlocked
from aiogram.types import InputFile
from configparser import ConfigParser

from helper import number_to_emoji

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Здесь можно установить уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
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


# Функция для удаления папок заведений и очистки файла ids.txt
async def remove_establishments_folders():
    try:
        # Путь к файлу с ID заведений
        ids_file = os.path.join(MAIN_FOLDER, 'ids', 'ids.txt')
        
        # Проверяем наличие файла ids.txt
        if not os.path.exists(ids_file):
            logging.error(f"Файл {ids_file} не найден.")
            return

        # Читаем ID заведений из файла
        with open(ids_file, 'r', encoding='utf-8') as f:
            establishment_ids = [line.strip() for line in f if line.strip()]

        logging.info(f"Удаление папок для {len(establishment_ids)} заведений.")

        # Удаляем папки заведений
        for establishment_id in establishment_ids:
            establishment_folder = os.path.join(MAIN_FOLDER, establishment_id)
            if os.path.exists(establishment_folder):
                try:
                    shutil.rmtree(establishment_folder)
                    logging.info(f"Папка для заведения {establishment_id} успешно удалена.")
                except Exception as e:
                    logging.error(f"Ошибка при удалении папки для заведения {establishment_id}: {e}")
            else:
                logging.warning(f"Папка для заведения {establishment_id} не найдена.")

        # Очищаем файл ids.txt
        with open(ids_file, 'w', encoding='utf-8') as f:
            f.write('')
        logging.info(f"Файл {ids_file} очищен.")

    except Exception as e:
        logging.error(f"Ошибка при удалении папок и очистке файла ids.txt: {e}")

# Function to send messages
async def send_daily_reports():
    try:
        logging.info("Начало отправки ежедневных отчетов")
        ids_file = os.path.join(MAIN_FOLDER, 'ids', 'ids.txt')
        users_file = os.path.join(os.getcwd(), 'users.json')

        # Load user mappings
        if not os.path.exists(users_file):
            print(f"Users mapping file not found at {users_file}")
            return

        with open(users_file, 'r', encoding='utf-8') as uf:
            users_mapping = json.load(uf)  # This should be a dict {establishment_id: [user_id, ...]}
        logging.info(f"Загружено {len(users_mapping)} записей из users.json")
        # Read establishment IDs
        if not os.path.exists(ids_file):
            print(f"IDs file not found at {ids_file}")
            return

        with open(ids_file, 'r', encoding='utf-8') as f:
            establishment_ids = [line.strip() for line in f if line.strip()]

        logging.info(f"Найдено {len(establishment_ids)} заведений в ids.txt")

        for establishment_id in establishment_ids:
            logging.info(f"Обработка заведения ID: {establishment_id}")
            establishment_folder = os.path.join(MAIN_FOLDER, establishment_id)
            if not os.path.exists(establishment_folder):
                print(f"Folder for establishment {establishment_id} not found.")
                continue

            # Get the users to send messages to for this establishment
            user_ids = users_mapping.get(establishment_id, [])
            if not user_ids:
                print(f"No users to send messages to for establishment {establishment_id}")
                continue
            else:
                logging.info(f"Пользователи для заведения {establishment_id}: {user_ids}")
            
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
            message_lines.append(f"📍 *{org_name}* 📍\n")
            today_str = datetime.now().strftime(" `%d.%m.%Y` \n")
            message_lines.append(today_str)

            rating_emoji = number_to_emoji(org_rate)
            message_lines.append(f"⭐️ _Рейтинг:_ {rating_emoji}")
            message_lines.append(f"\n📝 _Отзывы:_ {org_feedback}\n")

            message_lines.append("👨‍👩‍👦‍👦 _Конкуренты:_")
            total_concurrents = len(concurrents)
            for idx, c in enumerate(concurrents, start=1):
                is_last = idx == total_concurrents
                prefix = '└──' if is_last else '├──'
                circle = '🟢' if c['is_own'] else '🔴'
                line = f"{prefix} {circle} {c['name']} ({c['share']})"
                message_lines.append(line)

            message_text = '\n'.join(message_lines)
            
            logging.info(f"message_text {message_text}")

            # Send the message to each user
            for user_id in user_ids:
                logging.info(f"Отправка сообщения пользователю {user_id}")
                try:
                    if screenshot_base64:
                        # Декодируем изображение из base64
                        image_data = base64.b64decode(screenshot_base64)
                        photo = InputFile(BytesIO(image_data), filename='screenshot.png')
                        # Отправляем фото с подписью
                        await bot.send_photo(chat_id=int(user_id), photo=photo, caption=message_text,
                        parse_mode='Markdown')
                    else:
                        # Если изображения нет, отправляем только текст
                        await bot.send_message(chat_id=int(user_id), text=message_text,
                        parse_mode='Markdown')
                except BotBlocked:
                    logging.error(f"Бот заблокирован пользователем {user_id}")
                except Exception as e:
                    logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                
    except Exception as err:
        print(f"Error: {err}")


# Schedule the daily task
# Планирование ежедневной задачи
async def scheduler():
    while True:
        now = datetime.now()
        next_run = now.replace(hour=11, minute=11, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logging.info(f"Следующая отправка отчетов запланирована на {next_run} (через {wait_seconds} секунд)")
        await asyncio.sleep(wait_seconds)
        await send_daily_reports()
        await remove_establishments_folders()


# Start polling and scheduler
async def main():
    logging.info(f"MAIN_FOLDER установлен на: {MAIN_FOLDER}")
    asyncio.create_task(scheduler())
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())