import asyncio
import logging
import random
import sys
import platform
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import BOT_TOKEN, WORKOUT_TYPES, HEALTH_TIPS, INACTIVITY_TIMEOUT
from database import Database
from workout_manager import WorkoutSession
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import register_handlers
from states import UserStates
from collections import defaultdict
import signal

# Настройка правильного событийного цикла для Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Инициализация логгера
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словарь для хранения активных сессий
active_sessions = {}

# Словарь для отслеживания спама
spam_control = defaultdict(lambda: {"count": 0, "last_message_time": None})
SPAM_LIMIT = 5  # Максимальное количество сообщений
SPAM_TIME_WINDOW = 3  # Временное окно в секундах
SPAM_BLOCK_TIME = 30  # Время блокировки в секундах

# Флаг состояния бота
bot_is_running = True

# Инициализация базы данных
db = Database()

async def spam_middleware(handler, event, data):
    """Middleware для защиты от спама"""
    if not bot_is_running:
        return
        
    if isinstance(event, types.Message):
        user_id = event.from_user.id
        current_time = datetime.now()
        user_data = spam_control[user_id]

        # Проверяем, не заблокирован ли пользователь
        if user_data.get("blocked_until"):
            if current_time < user_data["blocked_until"]:
                remaining_time = (user_data["blocked_until"] - current_time).seconds
                await event.answer(f"Вы временно заблокированы за спам. Подождите {remaining_time} секунд.")
                return
            else:
                # Разблокировка пользователя
                user_data["blocked_until"] = None
                user_data["count"] = 0

        # Обновляем счетчик сообщений
        if user_data["last_message_time"]:
            time_diff = (current_time - user_data["last_message_time"]).seconds
            if time_diff < SPAM_TIME_WINDOW:
                user_data["count"] += 1
            else:
                user_data["count"] = 1
        else:
            user_data["count"] = 1

        user_data["last_message_time"] = current_time

        # Проверяем на спам
        if user_data["count"] > SPAM_LIMIT:
            user_data["blocked_until"] = current_time + timedelta(seconds=SPAM_BLOCK_TIME)
            await event.answer(f"Вы заблокированы на {SPAM_BLOCK_TIME} секунд за спам.")
            return

    # Если всё в порядке, передаем управление дальше
    return await handler(event, data)

# Регистрируем middleware
dp.message.outer_middleware(spam_middleware)

def handle_shutdown(signum, frame):
    """Обработчик сигнала завершения"""
    global bot_is_running
    bot_is_running = False
    logging.info("Получен сигнал завершения. Бот останавливается...")
    sys.exit(0)

# Регистрация обработчика сигналов
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def get_main_keyboard():
    """Создание основной клавиатуры"""
    builder = InlineKeyboardBuilder()
    
    # Основные разделы
    builder.add(InlineKeyboardButton(text="🏋️ Тренировки", callback_data="menu_workouts"))
    builder.add(InlineKeyboardButton(text="📊 Прогресс", callback_data="menu_progress"))
    builder.add(InlineKeyboardButton(text="🍳 Питание", callback_data="menu_nutrition"))
    builder.add(InlineKeyboardButton(text="⏰ Напоминания", callback_data="menu_reminders"))
    builder.add(InlineKeyboardButton(text="💡 Советы", callback_data="menu_tips"))
    
    builder.adjust(2)  # Размещаем кнопки в два столбца
    return builder.as_markup()

def get_workouts_keyboard():
    """Клавиатура раздела тренировок"""
    builder = InlineKeyboardBuilder()
    
    for key, value in WORKOUT_TYPES.items():
        builder.add(InlineKeyboardButton(text=value, callback_data=f"workout_{key}"))
    
    builder.add(InlineKeyboardButton(text="📋 Мои программы", callback_data="my_programs"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(2)
    return builder.as_markup()

def get_progress_keyboard():
    """Клавиатура раздела прогресса"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="⚖️ Записать вес", callback_data="record_weight"))
    builder.add(InlineKeyboardButton(text="📏 Записать измерения", callback_data="record_measurements"))
    builder.add(InlineKeyboardButton(text="📈 Статистика", callback_data="show_statistics"))
    builder.add(InlineKeyboardButton(text="📊 График прогресса", callback_data="show_progress_graph"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    
    builder.adjust(2)
    return builder.as_markup()

def get_reminders_keyboard():
    """Клавиатура раздела напоминаний"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🏋️ Напоминания о тренировках", callback_data="workout_reminders"))
    builder.add(InlineKeyboardButton(text="🍽 Напоминания о питании", callback_data="meal_reminders"))
    builder.add(InlineKeyboardButton(text="⚙️ Настройки напоминаний", callback_data="reminder_settings"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    
    builder.adjust(2)
    return builder.as_markup()

def get_tips_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🏋️ Советы по тренировкам", callback_data="workout_tips"))
    builder.add(InlineKeyboardButton(text="🥗 Советы по питанию", callback_data="nutrition_tips"))
    builder.add(InlineKeyboardButton(text="💪 Мотивация", callback_data="motivation_tips"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    
    builder.adjust(2)
    return builder.as_markup()

def get_exercise_keyboard(session: WorkoutSession):
    builder = InlineKeyboardBuilder()
    
    if session.current_exercise > 0:
        builder.add(InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_exercise"))
    
    if session.current_exercise < len(session.exercises) - 1:
        builder.add(InlineKeyboardButton(text="➡️ Следующее", callback_data="next_exercise"))
    
    builder.add(InlineKeyboardButton(text="❌ Завершить", callback_data="end_workout"))
    builder.adjust(2)
    return builder.as_markup()

async def check_inactive_sessions():
    while True:
        to_remove = []
        for user_id, session in active_sessions.items():
            if session.is_inactive(INACTIVITY_TIMEOUT):
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del active_sessions[user_id]
            try:
                await bot.send_message(
                    user_id,
                    "Тренировка была автоматически завершена из-за отсутствия активности."
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        
        await asyncio.sleep(60)

async def main():
    await db.create_tables()
    await register_handlers(dp)
    
    asyncio.create_task(check_inactive_sessions())
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        global bot_is_running
        bot_is_running = False
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Бот остановлен пользователем')
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        sys.exit(1)
