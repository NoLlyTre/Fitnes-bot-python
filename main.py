import logging
import asyncio
import sqlite3
import datetime
import sys
import time
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging.handlers
from collections import defaultdict
import os
from datetime import datetime, timedelta
from aiogram.client.session.aiohttp import AiohttpSession
import aiohttp

TOKEN = "7997378459:AAE4Sd0D-Sjbf-bvEfub7cHeVSIStKLMjuc"

# Инициализируем бота и диспетчер
bot = None  # Будет инициализирован в main()
dp = Dispatcher()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            'bot.log',
            maxBytes=10485760,
            backupCount=5,
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger(__name__)

class DatabasePool:
    def __init__(self, database_name: str):
        self.database_name = database_name
        self._pool = []
        self.max_connections = 10
        
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        if not self._pool:
            conn = await aiosqlite.connect(self.database_name)
            await conn.execute("PRAGMA journal_mode=WAL")
        else:
            conn = self._pool.pop()
            
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database error: {e}")
            await conn.rollback()
            raise
        else:
            await conn.commit()
        finally:
            if len(self._pool) < self.max_connections:
                self._pool.append(conn)
            else:
                await conn.close()

db_pool = DatabasePool('fitness_bot.db')

async def execute_db_query(query: str, params: tuple = None, fetch: bool = False):
    async with db_pool.acquire() as conn:
        try:
            cursor = await conn.execute(query, params or ())
            if fetch:
                return await cursor.fetchall()
            return None
        except Exception as e:
            logger.error(f"Database query error: {query}, params: {params}, error: {e}")
            raise

class UserStates(StatesGroup):
    WAITING_FOR_WEIGHT = State()
    WAITING_FOR_CALORIES = State()
    WAITING_FOR_MEAL = State()
    WAITING_FOR_REMINDER_TYPE = State()
    WAITING_FOR_REMINDER_TIME = State()
    WAITING_FOR_REMINDER_DAYS = State()
    WAITING_FOR_FOOD_NAME = State()

# Словарь с примерными калориями для распространенных продуктов (на 100 грамм)
FOOD_CALORIES = {
    "яблоко": 52,
    "банан": 89,
    "куриная грудка": 165,
    "рис": 130,
    "гречка": 343,
    "овсянка": 68,
    "творог": 103,
    "яйцо": 155,
    "молоко": 42,
    "хлеб": 265,
    "картофель": 77,
    "морковь": 41,
    "помидор": 18,
    "огурец": 15,
    "сыр": 364,
    "йогурт": 59,
    "макароны": 344,
    "говядина": 250,
    "лосось": 208,
    "авокадо": 160
}

@dp.callback_query(lambda c: c.data == "calorie_calculator")
async def process_calorie_calculator(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(UserStates.WAITING_FOR_FOOD_NAME)
    
    # Создаем клавиатуру с популярными продуктами
    food_keyboard = []
    current_row = []
    
    for food in list(FOOD_CALORIES.keys())[:12]:  # Показываем только первые 12 продуктов
        if len(current_row) == 2:
            food_keyboard.append(current_row)
            current_row = []
        current_row.append(InlineKeyboardButton(text=food, callback_data=f"food_{food}"))
    
    if current_row:
        food_keyboard.append(current_row)
    
    food_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    
    food_choice_keyboard = InlineKeyboardMarkup(inline_keyboard=food_keyboard)
    
    await callback_query.message.edit_text(
        "🧮 Калькулятор калорий\n\n"
        "Выберите продукт из списка или введите его название.\n"
        "Я подскажу количество калорий на 100 грамм продукта.",
        reply_markup=food_choice_keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("food_"))
async def process_food_choice(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    food_name = callback_query.data.replace("food_", "")
    calories = FOOD_CALORIES.get(food_name)
    
    await callback_query.message.edit_text(
        f"🍽 {food_name.capitalize()}:\n"
        f"Калорийность: {calories} ккал на 100 грамм\n\n"
        "Хотите рассчитать калории для другого продукта?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Рассчитать ещё", callback_data="calorie_calculator")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_tracking")]
        ])
    )

@dp.message(UserStates.WAITING_FOR_FOOD_NAME)
async def process_food_name(message: types.Message, state: FSMContext):
    food_name = message.text.lower()
    calories = FOOD_CALORIES.get(food_name)
    
    if calories:
        await message.answer(
            f"🍽 {food_name.capitalize()}:\n"
            f"Калорийность: {calories} ккал на 100 грамм\n\n"
            "Хотите рассчитать калории для другого продукта?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Рассчитать ещё", callback_data="calorie_calculator")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_tracking")]
            ])
        )
    else:
        similar_foods = []
        for food in FOOD_CALORIES:
            if food.startswith(food_name[:2]):
                similar_foods.append(food)
        
        if similar_foods:
            text = "Продукт не найден. Возможно, вы имели в виду:\n" + "\n".join(similar_foods)
        else:
            text = "Извините, такой продукт не найден в базе данных. Попробуйте другой продукт."
        
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="calorie_calculator")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_tracking")]
            ])
        )
    
    await state.clear()

# Заменяем клавиатуры на инлайн версии
main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💪 Мотивация", callback_data="motivation")],
        [InlineKeyboardButton(text="🏋️ Тренировка", callback_data="workout")],
        [InlineKeyboardButton(text="💡 Советы по здоровью", callback_data="health_tips")],
        [InlineKeyboardButton(text="📈 Прогресс", callback_data="progress")],
        [InlineKeyboardButton(text="🍴 Рецепты", callback_data="recipes")],
        [InlineKeyboardButton(text="⏰ Управление напоминаниями", callback_data="manage_reminders")]
    ]
)

muscle_groups_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🦾 Руки", callback_data="muscles_arms"),
            InlineKeyboardButton(text="🦵 Ноги", callback_data="muscles_legs")
        ],
        [
            InlineKeyboardButton(text="🫁 Грудь", callback_data="muscles_chest"),
            InlineKeyboardButton(text="🔙 Спина", callback_data="muscles_back")
        ],
        [
            InlineKeyboardButton(text="🦴 Плечи", callback_data="muscles_shoulders"),
            InlineKeyboardButton(text="💪 Пресс", callback_data="muscles_abs")
        ],
        [InlineKeyboardButton(text="🔄 Все тело", callback_data="muscles_full")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
    ]
)

recipes_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔻 Рецепты для похудения", callback_data="recipes_loss")],
        [InlineKeyboardButton(text="🔺 Рецепты для набора массы", callback_data="recipes_gain")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
    ]
)

weight_loss_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🥗 Салат с курицей", callback_data="recipe_chicken_salad")],
        [InlineKeyboardButton(text="🐟 Запеченная рыба с овощами", callback_data="recipe_fish")],
        [InlineKeyboardButton(text="🥑 Авокадо-тост с яйцом", callback_data="recipe_avocado")],
        [InlineKeyboardButton(text="🍲 Овощной суп", callback_data="recipe_veggie_soup")],
        [InlineKeyboardButton(text="🔙 Назад к выбору типа", callback_data="back_to_recipes")]
    ]
)

weight_gain_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🥩 Стейк с рисом", callback_data="recipe_steak")],
        [InlineKeyboardButton(text="🥜 Протеиновый смузи", callback_data="recipe_smoothie")],
        [InlineKeyboardButton(text="🍗 Паста с курицей", callback_data="recipe_pasta")],
        [InlineKeyboardButton(text="🥞 Протеиновые блины", callback_data="recipe_pancakes")],
        [InlineKeyboardButton(text="🔙 Назад к выбору типа", callback_data="back_to_recipes")]
    ]
)

tracking_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Записать приём пищи", callback_data="record_meal")],
        [InlineKeyboardButton(text="⚖️ Обновить вес", callback_data="update_weight")],
        [InlineKeyboardButton(text="📊 Показать статистику", callback_data="show_stats")],
        [InlineKeyboardButton(text="🎯 Установить цель калорий", callback_data="set_calories")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
    ]
)

reminder_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏋️ Тренировка", callback_data="reminder_workout")],
        [InlineKeyboardButton(text="🍽 Прием пищи", callback_data="reminder_meal")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
)

cancel_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
)

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=1):
        self.rate_limit = rate_limit
        self.users = defaultdict(lambda: {"last_request": 0, "request_count": 0})
        
    async def __call__(self, handler, event: types.Message, data):
        user_id = event.from_user.id
        current_time = time.time()
        user_data = self.users[user_id]
        
        if current_time - user_data["last_request"] > 1:
            user_data["request_count"] = 0
            
        user_data["request_count"] += 1
        user_data["last_request"] = current_time
        
        if user_data["request_count"] > self.rate_limit:
            await event.answer("Пожалуйста, подождите немного перед следующим запросом.")
            return
            
        return await handler(event, data)

dp.message.middleware(ThrottlingMiddleware())

last_shown_plan = {}

exercises = {
    "🦾 Руки": [
        [
            {
                "name": "Отжимания от пола",
                "description": "3 подхода по 12-15 повторений\n"
                             "1. Примите упор лёжа\n"
                             "2. Опуститесь, сгибая руки в локтях\n"
                             "3. Вернитесь в исходное положение",
                "image": "https://i.imgur.com/07aHFUN.jpg"
            },
            {
                "name": "Сгибания рук с гантелями",
                "description": "4 подхода по 10-12 повторений\n"
                             "1. Возьмите гантели\n"
                             "2. Сгибайте руки, поднимая вес к плечам\n"
                             "3. Медленно опускайте",
                "image": "https://i.imgur.com/Knwq7Ob.jpg"
            }
        ]
    ],
    "🦵 Ноги": [
        [
            {
                "name": "Приседания",
                "description": "4 подхода по 15-20 повторений\n"
                             "1. Встаньте, ноги на ширине плеч\n"
                             "2. Опуститесь, сгибая колени\n"
                             "3. Вернитесь в исходное положение",
                "image": "https://i.imgur.com/d8BbB6g.jpg"
            },
            {
                "name": "Выпады",
                "description": "3 подхода по 12 повторений на каждую ногу\n"
                             "1. Сделайте шаг вперед\n"
                             "2. Опуститесь, сгибая колени\n"
                             "3. Вернитесь в исходное положение",
                "image": "https://i.imgur.com/rzk9UVG.jpg"
            }
        ]
    ],
    "🫁 Грудь": [
        [
            {
                "name": "Отжимания с широкой постановкой",
                "description": "4 подхода по 12-15 повторений\n"
                             "1. Примите упор лёжа, руки шире плеч\n"
                             "2. Опуститесь, сгибая руки\n"
                             "3. Вернитесь в исходное положение",
                "image": "https://i.imgur.com/0sGbRRS.jpg"
            }
        ]
    ],
    "🔙 Спина": [
        [
            {
                "name": "Подтягивания",
                "description": "3 подхода по максимуму\n"
                             "1. Возьмитесь за перекладину\n"
                             "2. Подтянитесь до подбородка\n"
                             "3. Медленно опуститесь",
                "image": "https://i.imgur.com/hiro87U.jpg"
            }
        ]
    ],
    "🦴 Плечи": [
        [
            {
                "name": "Армейский жим",
                "description": "4 подхода по 10-12 повторений\n"
                             "1. Возьмите гантели на уровне плеч\n"
                             "2. Выжмите вес вверх\n"
                             "3. Медленно опустите",
                "image": "https://i.imgur.com/f2869dN.jpg"
            }
        ]
    ],
    "💪 Пресс": [
        [
            {
                "name": "Скручивания",
                "description": "3 подхода по 20 повторений\n"
                             "1. Лягте на спину\n"
                             "2. Поднимите корпус, напрягая пресс\n"
                             "3. Вернитесь в исходное положение",
                "image": "https://i.imgur.com/w5uO4kj.jpg"
            }
        ]
    ],
    "🔄 Все тело": [
        [
            {
                "name": "Берпи",
                "description": "3 подхода по 10 повторений\n"
                             "1. Примите упор лёжа\n"
                             "2. Сделайте отжимание\n"
                             "3. Прыжком примите упор присев\n"
                             "4. Выпрыгните вверх",
                "image": "https://i.imgur.com/Oeb2bMc.jpg"
            }
        ]
    ]
}

exercise_recommendations = {
    "🦾 Руки": {
        "tips": [
            "🔹 Всегда разминайте локтевые суставы перед тренировкой",
            "🔹 Следите за тем, чтобы локти не расходились в стороны при отжиманиях",
            "🔹 Выполняйте движения в полной амплитуде",
            "🔹 Контролируйте негативную фазу движения (опускание)",
            "🔹 Не используйте слишком большой вес - техника важнее"
        ],
        "technique": "Для максимальной эффективности тренировки рук:\n"
                    "1. Чередуйте упражнения на бицепс и трицепс\n"
                    "2. Делайте паузу 1-2 секунды в пиковом сокращении\n"
                    "3. Не раскачивайтесь во время выполнения упражнений"
    },
    "🦵 Ноги": {
        "tips": [
            "🔹 Колени не должны выходить за носки при приседаниях",
            "🔹 Держите спину прямой во время всех упражнений",
            "🔹 Приземляйтесь мягко после прыжковых упражнений",
            "🔹 Следите за равномерным распределением веса на стопах",
            "🔹 Не забывайте про растяжку после тренировки"
        ],
        "technique": "Правильная техника для ног:\n"
                    "1. Начинайте движение от бедер, а не колен\n"
                    "2. Опускайтесь в присед до параллели с полом\n"
                    "3. Стопы должны быть направлены слегка наружу"
    },
    "🫁 Грудь": {
        "tips": [
            "🔹 Сводите лопатки перед каждым повторением",
            "🔹 Не опускайте локти ниже уровня груди",
            "🔹 Держите естественный прогиб в пояснице",
            "🔹 Дышите равномерно: выдох на усилии",
            "🔹 Меняйте углы выполнения для разной нагрузки"
        ],
        "technique": "Техника выполнения упражнений на грудь:\n"
                    "1. Опускайтесь медленно и контролируемо\n"
                    "2. Не разводите локти слишком широко\n"
                    "3. Полностью выпрямляйте руки в верхней точке"
    },
    "🔙 Спина": {
        "tips": [
            "🔹 Начинайте движение с оттягивания лопаток вниз",
            "🔹 Не используйте инерцию тела",
            "🔹 Старайтесь чувствовать работу мышц спины",
            "🔹 Держите взгляд направленным вперед",
            "🔹 Не забывайте про нижнюю часть спины"
        ],
        "technique": "Ключевые моменты техники для спины:\n"
                    "1. Тяните вес локтями, а не бицепсами\n"
                    "2. Держите грудь расправленной\n"
                    "3. Избегайте раскачиваний во время упражнений"
    },
    "🦴 Плечи": {
        "tips": [
            "🔹 Не поднимайте вес рывками",
            "🔹 Следите за положением локтей",
            "🔹 Держите корпус стабильным",
            "🔹 Не поднимайте руки выше уровня плеч при боковых подъемах",
            "🔹 Разминайте плечевые суставы перед тренировкой"
        ],
        "technique": "Техника выполнения упражнений на плечи:\n"
                    "1. Начинайте с легкого веса для разминки\n"
                    "2. Удерживайте паузу в верхней точке\n"
                    "3. Контролируйте движение при опускании веса"
    },
    "💪 Пресс": {
        "tips": [
            "🔹 Не тяните себя за шею при скручиваниях",
            "🔹 Держите поясницу прижатой к полу",
            "🔹 Выполняйте упражнения медленно и контролируемо",
            "🔹 Следите за дыханием",
            "🔹 Чередуйте упражнения на верхний и нижний пресс"
        ],
        "technique": "Правильная техника для пресса:\n"
                    "1. Напрягайте мышцы живота перед каждым повторением\n"
                    "2. Делайте упражнения через силу мышц, а не инерцию\n"
                    "3. Держите подбородок слегка приподнятым"
    },
    "🔄 Все тело": {
        "tips": [
            "🔹 Соблюдайте правильное дыхание",
            "🔹 Делайте достаточные перерывы между подходами",
            "🔹 Следите за техникой даже при усталости",
            "🔹 Пейте воду между подходами",
            "🔹 Начинайте с более легкой версии упражнений"
        ],
        "technique": "Техника выполнения круговой тренировки:\n"
                    "1. Начинайте с разминки всего тела\n"
                    "2. Чередуйте упражнения на разные группы мышц\n"
                    "3. Следите за пульсом и не перенапрягайтесь"
    }
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "Привет! Я твой фитнес-бот. Вот что я могу:\n"
        "1. 💪 Мотивация — вдохновляющие цитаты\n"
        "2. 🏋️ Тренировка — персональный план тренировок\n"
        "3. 💡 Советы по здоровью — полезные рекомендации\n"
        "4. 📈 Прогресс — как отслеживать достижения\n"
        "5. 🍴 Рецепты — здоровые и вкусные блюда\n"
        "6. ⏰ Управление напоминаниями — настройка уведомлений о тренировках и приемах пищи"
    )
    
    try:
        await message.answer(welcome_text, reply_markup=main_keyboard)
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

async def init_db():
    queries = [
        '''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            target_calories INTEGER DEFAULT 2000,
            target_weight REAL,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS weight_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            weight REAL,
            date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''',
        '''CREATE TABLE IF NOT EXISTS meal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_type TEXT,
            calories INTEGER,
            date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''',
        '''CREATE TABLE IF NOT EXISTS shown_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quote_text TEXT,
            shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''',
        '''CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reminder_type TEXT,
            reminder_time TEXT,
            days TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''',
        'CREATE INDEX IF NOT EXISTS idx_weight_records_user_date ON weight_records(user_id, date)',
        'CREATE INDEX IF NOT EXISTS idx_meal_records_user_date ON meal_records(user_id, date)',
        'CREATE INDEX IF NOT EXISTS idx_shown_quotes_user ON shown_quotes(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id)'
    ]
    
    for query in queries:
        await execute_db_query(query)

async def get_random_quote(user_id: int) -> str:
    try:
        # Используем абсолютный путь к файлу
        quotes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quotes.txt')
        # Читаем все цитаты из файла
        with open(quotes_path, 'r', encoding='utf-8') as file:
            all_quotes = [quote.strip() for quote in file.readlines() if quote.strip()]
        
        # Получаем историю показанных цитат для пользователя
        shown_quotes = await execute_db_query(
            "SELECT quote_text FROM shown_quotes WHERE user_id = ?",
            (user_id,),
            fetch=True
        )
        shown_quotes_set = {quote[0] for quote in shown_quotes}
        
        # Находим непоказанные цитаты
        available_quotes = [quote for quote in all_quotes if quote not in shown_quotes_set]
        
        # Если все цитаты были показаны, очищаем историю
        if not available_quotes:
            await execute_db_query(
                "DELETE FROM shown_quotes WHERE user_id = ?",
                (user_id,)
            )
            available_quotes = all_quotes
        
        # Выбираем случайную цитату из доступных
        quote = random.choice(available_quotes)
        
        # Сохраняем выбранную цитату в историю
        await execute_db_query(
            "INSERT INTO shown_quotes (user_id, quote_text) VALUES (?, ?)",
            (user_id, quote)
        )
        
        return quote
    except Exception as e:
        logger.error(f"Error reading quotes file: {e}")
        return "\"Самый трудный шаг — это начало, все остальное проще!\""

@dp.message(lambda message: message.text == "💪 Мотивация")
async def send_motivation(message: types.Message):
    try:
        quote = await get_random_quote(message.from_user.id)
        await message.answer(
            "Мотивация — это ключ к успеху! Вот несколько советов, которые могут тебе помочь:\n"
            "- Постоянство в действиях — главная составляющая успеха.\n"
            "- Ставь конкретные цели и записывай их.\n"
            "- Не бойся неудач — каждый шаг в любом случае приближает тебя к успеху.\n\n"
            f"Цитата дня: {quote} 💫"
        )
    except Exception as e:
        logger.error(f"Error in send_motivation for user {message.from_user.id}: {e}")
        await message.answer(
            "Произошла ошибка при получении мотивационной цитаты. "
            "Но помните: каждый день - это новая возможность стать лучше! 💪"
        )

@dp.message(lambda message: message.text == "🏋️ Тренировка")
async def show_muscle_groups(message: types.Message):
    await message.answer(
        "Выберите группу мышц для тренировки:",
        reply_markup=muscle_groups_keyboard
    )

@dp.message(lambda message: message.text in exercises.keys())
async def show_exercises(message: types.Message):
    try:
        muscle_group = message.text
        all_plans = exercises[muscle_group]
        
        current_plan_index = last_shown_plan.get(muscle_group, -1)
        
        next_plan_index = (current_plan_index + 1) % len(all_plans)
        last_shown_plan[muscle_group] = next_plan_index
        
        workout = all_plans[next_plan_index]
        
        await message.answer(
            f"🏋️‍♂️ План тренировки {next_plan_index + 1} для {muscle_group}:"
        )
        
        for exercise in workout:
            try:
                await message.answer_photo(
                    photo=exercise["image"],
                    caption=f"*{exercise['name']}*\n\n{exercise['description']}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error sending exercise image: {e}")
                await message.answer(
                    f"*{exercise['name']}*\n\n{exercise['description']}",
                    parse_mode="Markdown"
                )
        
        recommendations = exercise_recommendations.get(muscle_group, {})
        if recommendations:
            tips_text = "\n".join(recommendations["tips"])
            technique_text = recommendations["technique"]
            
            await message.answer(
                f"🎯 Рекомендации для {muscle_group}:\n\n"
                f"{tips_text}\n\n"
                f"⚡️ Техника выполнения:\n"
                f"{technique_text}"
            )
        
    except Exception as e:
        logger.error(f"Error in show_exercises: {e}")
        await message.answer("Произошла ошибка при показе упражнений. Попробуйте позже.")

@dp.message(lambda message: message.text == "💡 Советы по здоровью")
async def send_health_tips(message: types.Message):
    await message.answer(
        "Вот несколько простых и полезных советов для поддержания здоровья:\n"
        "- Пей достаточное количество воды каждый день (2-3 литра в зависимости от веса). 💧\n"
        "- Занимайся физической активностью хотя бы 30 минут в день. 🏃‍♂️\n"
        "- Спи не менее 7-8 часов — хороший сон способствует восстановлению организма. 😴\n"
        "- Следи за уровнем стресса и отдыхай, когда это необходимо. 🧘‍♀️\n"
        "- Не забывай про регулярные медицинские осмотры для предотвращения заболеваний. 🩺"
    )
    
@dp.message(lambda message: message.text == "📈 Прогресс")
async def progress_menu(message: types.Message):
    await message.answer(
        "Меню отслеживания прогресса:",
        reply_markup=tracking_keyboard
    )

@dp.message(lambda message: message.text == "🍴 Рецепты")
async def send_recipes(message: types.Message):
    await message.answer(
        "Выберите тип рецептов в зависимости от вашей цели: 🎯",
        reply_markup=recipes_keyboard
    )

@dp.message(lambda message: message.text == "🔻 Рецепты для похудения")
async def weight_loss_recipes(message: types.Message):
    await message.answer(
        "Выберите рецепт для похудения: 🥗",
        reply_markup=weight_loss_keyboard
    )

@dp.message(lambda message: message.text == "🔺 Рецепты для набора массы")
async def weight_gain_recipes(message: types.Message):
    await message.answer(
        "Выберите рецепт для набора массы: 💪",
        reply_markup=weight_gain_keyboard
    )

def calculate_portions(weight: float, recipe_name: str) -> dict:
    base_recipes = {
        "🥗 Салат с курицей": {
            "base_weight": 70,
            "ingredients": {
                "Куриная грудь": lambda w: int(w * 1.5),
                "Листья салата": lambda w: int(w * 2),
                "Помидоры": lambda w: int(w * 1),
                "Огурцы": lambda w: int(w * 1),
                "Оливковое масло": lambda w: int(w * 0.2)
            },
            "calories": lambda w: int(w * 3),
            "instructions": "1. Отварите куриную грудь\n2. Нарежьте овощи\n3. Смешайте все ингредиенты\n4. Заправьте оливковым маслом"
        },
        "🐟 Запеченная рыба с овощами": {
            "base_weight": 70,
            "ingredients": {
                "Филе рыбы": lambda w: int(w * 2),
                "Брокколи": lambda w: int(w * 1.5),
                "Морковь": lambda w: int(w * 1),
                "Лук": lambda w: int(w * 0.5),
                "Оливковое масло": lambda w: int(w * 0.2)
            },
            "calories": lambda w: int(w * 2.5),
            "instructions": "1. Подготовьте филе рыбы\n2. Нарежьте овощи\n3. Выложите все на противень\n4. Запекайте 20-25 минут при 180°C"
        },
        "🥑 Авокадо-тост с яйцом": {
            "base_weight": 70,
            "ingredients": {
                "Цельнозерновой хлеб": lambda w: int(w * 0.5),
                "Авокадо": lambda w: int(w * 0.5),
                "Яйцо": lambda w: 1,
                "Помидоры черри": lambda w: int(w * 0.3),
                "Зелень": lambda w: int(w * 0.1)
            },
            "calories": lambda w: int(w * 2),
            "instructions": "1. Поджарьте хлеб\n2. Разомните авокадо\n3. Приготовьте яйцо пашот\n4. Выложите авокадо на хлеб\n5. Сверху положите яйцо и украсьте помидорами и зеленью"
        },
        "🍲 Овощной суп": {
            "base_weight": 70,
            "ingredients": {
                "Морковь": lambda w: int(w * 0.7),
                "Картофель": lambda w: int(w * 1),
                "Капуста": lambda w: int(w * 0.8),
                "Лук": lambda w: int(w * 0.3),
                "Сельдерей": lambda w: int(w * 0.3),
                "Помидоры": lambda w: int(w * 0.5)
            },
            "calories": lambda w: int(w * 1.5),
            "instructions": "1. Нарежьте все овощи\n2. Обжарьте лук и морковь\n3. Добавьте остальные овощи и залейте водой\n4. Варите 20-25 минут\n5. Добавьте зелень по вкусу"
        },
        "🥩 Стейк с рисом": {
            "base_weight": 70,
            "ingredients": {
                "Говяжий стейк": lambda w: int(w * 2.5),
                "Рис": lambda w: int(w * 2),
                "Овощи гриль": lambda w: int(w * 1.5),
                "Оливковое масло": lambda w: int(w * 0.3),
                "Специи": lambda w: int(w * 0.1)
            },
            "calories": lambda w: int(w * 5),
            "instructions": "1. Замаринуйте стейк в специях\n2. Отварите рис\n3. Приготовьте стейк на гриле\n4. Обжарьте овощи\n5. Подавайте с соусом"
        },
        "🥜 Протеиновый смузи": {
            "base_weight": 70,
            "ingredients": {
                "Банан": lambda w: int(w * 1.5),
                "Молоко": lambda w: int(w * 2.5),
                "Протеин": lambda w: int(w * 1),
                "Арахисовая паста": lambda w: int(w * 0.5),
                "Мед": lambda w: int(w * 0.2)
            },
            "calories": lambda w: int(w * 4),
            "instructions": "1. Очистите банан\n2. Смешайте все ингредиенты в блендере\n3. Взбивайте до однородной массы\n4. При желании добавьте лед"
        },
        "🍗 Паста с курицей": {
            "base_weight": 70,
            "ingredients": {
                "Паста": lambda w: int(w * 2),
                "Куриная грудка": lambda w: int(w * 2),
                "Сливки": lambda w: int(w * 1),
                "Пармезан": lambda w: int(w * 0.5),
                "Чеснок": lambda w: int(w * 0.1)
            },
            "calories": lambda w: int(w * 4.5),
            "instructions": "1. Отварите пасту\n2. Обжарьте курицу с чесноком\n3. Добавьте сливки\n4. Смешайте с пастой\n5. Посыпьте тертым пармезаном"
        },
        "🥞 Протеиновые блины": {
            "base_weight": 70,
            "ingredients": {
                "Овсяная мука": lambda w: int(w * 1.5),
                "Протеин": lambda w: int(w * 1),
                "Яйца": lambda w: 2,
                "Молоко": lambda w: int(w * 1.5),
                "Мед": lambda w: int(w * 0.3)
            },
            "calories": lambda w: int(w * 3.5),
            "instructions": "1. Смешайте все ингредиенты\n2. Взбейте до однородной массы\n3. Жарьте на среднем огне\n4. Подавайте с медом или джемом"
        }
    }
    
    recipe = base_recipes.get(recipe_name)
    if not recipe:
        return None
        
    result = {
        "ingredients": {},
        "calories": recipe["calories"](weight),
        "instructions": recipe["instructions"]
    }
    
    for ingredient, calc in recipe["ingredients"].items():
        result["ingredients"][ingredient] = calc(weight)
        
    return result

async def send_recipe_details_inline(message: types.Message, recipe_name: str):
    try:
        recipe_images = {
            "🥗 Салат с курицей": "https://i.imgur.com/ZeKqypn.jpeg",
            "🐟 Запеченная рыба с овощами": "https://i.imgur.com/3sBXm68.jpg",
            "🥑 Авокадо-тост с яйцом": "https://i.imgur.com/BADKEq0.jpg",
            "🍲 Овощной суп": "https://i.imgur.com/Sx86Nvs.jpg",
            "🥩 Стейк с рисом": "https://i.imgur.com/3pXM5nN.jpg",
            "🥜 Протеиновый смузи": "https://i.imgur.com/N2dtgHZ.jpg",
            "🍗 Паста с курицей": "https://i.imgur.com/DAAQd6O.jpg",
            "🥞 Протеиновые блины": "https://i.imgur.com/THYuSsM.jpg"
        }

        # Определяем, какой тип рецепта это
        weight_loss_recipes = ["🥗 Салат с курицей", "🐟 Запеченная рыба с овощами", "🥑 Авокадо-тост с яйцом", "🍲 Овощной суп"]
        is_weight_loss = recipe_name in weight_loss_recipes

        # Получаем последний записанный вес пользователя
        weight_record = await execute_db_query(
            """SELECT weight FROM weight_records 
               WHERE user_id = ? 
               ORDER BY date DESC LIMIT 1""",
            (message.chat.id,),
            fetch=True
        )
        
        if not weight_record:
            await message.edit_text(
                "Пожалуйста, сначала введите ваш вес через меню 'Прогресс' -> '⚖️ Обновить вес'",
                reply_markup=tracking_keyboard
            )
            return

        weight = weight_record[0][0]
        recipe = calculate_portions(weight, recipe_name)
        
        if recipe:
            recipe_text = f"{recipe_name}\n\nИнгредиенты (расчет на {weight} кг веса):\n"
            for ingredient, amount in recipe["ingredients"].items():
                recipe_text += f"- {ingredient}: {amount} г\n"
            
            recipe_text += f"\nКалорийность порции: {recipe['calories']} ккал"
            recipe_text += f"\n\nПриготовление:\n{recipe['instructions']}"
            
            try:
                # Сначала удаляем старое сообщение
                await message.delete()
                # Отправляем новое сообщение с фото и рецептом
                await message.answer_photo(
                    photo=recipe_images[recipe_name],
                    caption=recipe_text,
                    reply_markup=weight_loss_keyboard if is_weight_loss else weight_gain_keyboard
                )
            except Exception as e:
                logger.error(f"Error sending recipe photo: {e}")
                # Если не удалось отправить фото, отправляем только текст
                await message.answer(
                    recipe_text,
                    reply_markup=weight_loss_keyboard if is_weight_loss else weight_gain_keyboard
                )
        else:
            await message.edit_text(
                "Извините, рецепт временно недоступен",
                reply_markup=recipes_keyboard
            )
            
    except Exception as e:
        logger.error(f"Error in send_recipe_details_inline: {e}")
        await message.answer(
            "Произошла ошибка при получении рецепта. Попробуйте позже.",
            reply_markup=recipes_keyboard
        )

@dp.message(lambda message: message.text == "🔙 Назад к выбору типа")
async def back_to_recipe_type(message: types.Message):
    await message.answer(
        "Выберите тип рецептов:",
        reply_markup=recipes_keyboard
    )

@dp.message(lambda message: message.text == "❌ Отмена")
async def cancel_action(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_keyboard)
    else:
        await message.answer("Нет активного действия для отмены.", reply_markup=main_keyboard)

def calculate_calories(food_name: str, grams: float) -> int:
    """Рассчитывает калории для заданного количества продукта"""
    calories_per_100g = FOOD_CALORIES.get(food_name.lower())
    if calories_per_100g:
        return int((calories_per_100g * grams) / 100)
    return None

@dp.message(UserStates.WAITING_FOR_MEAL)
async def process_meal(message: types.Message, state: FSMContext):
    try:
        # Проверяем формат: "продукт граммы" или "тип_приема_пищи - калории"
        if " - " in message.text:
            meal_type, calories = message.text.split('-')
            meal_type = meal_type.strip().lower()
            calories = int(calories.strip())
        else:
            # Пытаемся разобрать формат "продукт граммы"
            try:
                food_name, grams = message.text.rsplit(" ", 1)
                food_name = food_name.strip().lower()
                grams = float(grams.strip())
                
                calories = calculate_calories(food_name, grams)
                if calories is None:
                    similar_foods = []
                    for food in FOOD_CALORIES:
                        if food.startswith(food_name[:2]):
                            similar_foods.append(food)
                    
                    if similar_foods:
                        await message.answer(
                            "Продукт не найден. Возможно, вы имели в виду:\n" + 
                            "\n".join(similar_foods) + 
                            "\n\nВведите название из списка и количество грамм",
                            reply_markup=cancel_keyboard
                        )
                    else:
                        await message.answer(
                            "Продукт не найден в базе. Попробуйте другой продукт или используйте формат:\n"
                            "тип_приема_пищи - калории",
                            reply_markup=cancel_keyboard
                        )
                    return
                
                meal_type = "прием пищи"
            except ValueError:
                await message.answer(
                    "Неверный формат. Используйте:\n"
                    "1. [продукт] [граммы] (например: яблоко 100)\n"
                    "2. [тип_приема_пищи] - [калории] (например: завтрак - 500)",
                    reply_markup=cancel_keyboard
                )
                return
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        await execute_db_query(
            "INSERT INTO meal_records (user_id, meal_type, calories, date) VALUES (?, ?, ?, ?)",
            (message.from_user.id, meal_type, calories, current_date)
        )
        
        # Формируем сообщение об успешной записи
        if " - " not in message.text:
            await message.answer(
                f"✅ Записано: {food_name.capitalize()} - {grams}г\n"
                f"Калорийность: {calories} ккал",
                reply_markup=tracking_keyboard
            )
        else:
            await message.answer(
                f"✅ {meal_type.capitalize()} записан: {calories} ккал",
                reply_markup=tracking_keyboard
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_meal for user {message.from_user.id}: {e}")
        await message.answer(
            "Произошла ошибка при записи. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )
        await state.clear()

@dp.message(lambda message: message.text == "⚖️ Обновить вес")
async def update_weight(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.WAITING_FOR_WEIGHT)
    await message.answer(
        "Введите ваш текущий вес в килограммах (например: 70.5)\n\n"
        "Для отмены нажмите кнопку ❌ Отмена",
        reply_markup=cancel_keyboard
    )

@dp.message(UserStates.WAITING_FOR_WEIGHT)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight < 30 or weight > 300:
            await message.answer(
                "Пожалуйста, введите реальный вес (от 30 до 300 кг)\n"
                "Или нажмите ❌ Отмена для отмены действия",
                reply_markup=cancel_keyboard
            )
            return

        current_date = datetime.now().strftime('%Y-%m-%d')
        await execute_db_query(
            "INSERT INTO weight_records (user_id, weight, date) VALUES (?, ?, ?)",
            (message.from_user.id, weight, current_date)
        )

        await message.answer(f"Вес {weight} кг успешно записан! 📝", reply_markup=tracking_keyboard)
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число (например: 70.5)\n"
            "Или нажмите ❌ Отмена для отмены действия",
            reply_markup=cancel_keyboard
        )
    except Exception as e:
        logger.error(f"Error in process_weight for user {message.from_user.id}: {e}")
        await message.answer(
            "Произошла ошибка при записи веса. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )
        await state.clear()

@dp.message(lambda message: message.text == "🎯 Установить цель калорий")
async def set_calories_goal(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.WAITING_FOR_CALORIES)
    await message.answer(
        "Введите вашу цель по калориям на день (например: 2000)\n\n"
        "Для отмены нажмите кнопку ❌ Отмена",
        reply_markup=cancel_keyboard
    )

@dp.message(UserStates.WAITING_FOR_CALORIES)
async def process_calories_goal(message: types.Message, state: FSMContext):
    try:
        calories = int(message.text)
        if calories < 1200 or calories > 5000:
            await message.answer(
                "Пожалуйста, введите реальную цель (от 1200 до 5000 ккал)\n"
                "Или нажмите ❌ Отмена для отмены действия",
                reply_markup=cancel_keyboard
            )
            return

        await execute_db_query(
            "INSERT OR REPLACE INTO users (user_id, target_calories) VALUES (?, ?)",
            (message.from_user.id, calories)
        )

        await message.answer(f"Цель {calories} ккал в день установлена! 🎯", reply_markup=tracking_keyboard)
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите целое число (например: 2000)\n"
            "Или нажмите ❌ Отмена для отмены действия",
            reply_markup=cancel_keyboard
        )
    except Exception as e:
        logger.error(f"Error in process_calories_goal for user {message.from_user.id}: {e}")
        await message.answer(
            "Произошла ошибка при установке цели. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )
        await state.clear()

@dp.message(lambda message: message.text == "📊 Показать статистику")
async def show_statistics(message: types.Message):
    try:
        # Получаем записи веса
        weight_records = await execute_db_query(
            """SELECT weight, date FROM weight_records 
               WHERE user_id = ? 
               ORDER BY date ASC LIMIT 30""",
            (message.chat.id,),
            fetch=True
        )
        
        # Получаем записи калорий
        calorie_records = await execute_db_query(
            """SELECT SUM(calories) as total_calories, date 
               FROM meal_records 
               WHERE user_id = ? 
               GROUP BY date 
               ORDER BY date ASC LIMIT 30""",
            (message.chat.id,),
            fetch=True
        )
        
        if not weight_records and not calorie_records:
            await message.answer(
                "У вас пока нет записей для анализа. Начните вести учет веса и питания!",
                reply_markup=tracking_keyboard
            )
            return
            
        # Создаем текстовый отчет
        report = "📊 Статистика за последние 30 дней:\n\n"
        
        if weight_records:
            latest_weight = weight_records[-1][0]
            first_weight = weight_records[0][0]
            weight_change = latest_weight - first_weight
            
            report += f"💪 Вес:\n"
            report += f"Текущий: {latest_weight} кг\n"
            report += f"Изменение: {weight_change:+.1f} кг\n\n"
        
        if calorie_records:
            avg_calories = sum(record[0] for record in calorie_records) / len(calorie_records)
            report += f"🍽 Калории:\n"
            report += f"Среднее потребление: {int(avg_calories)} ккал/день\n"
            
            # Получаем цель по калориям
            target_result = await execute_db_query(
                "SELECT target_calories FROM users WHERE user_id = ?",
                (message.chat.id,),
                fetch=True
            )
            if target_result:
                target_calories = target_result[0][0]
                report += f"Цель: {target_calories} ккал/день\n"
        
        await message.answer(report, reply_markup=tracking_keyboard)
        
    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        await message.answer(
            "Произошла ошибка при формировании статистики. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )

@dp.message(lambda message: message.text == "🔙 Назад в меню")
async def back_to_main_menu(message: types.Message):
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=main_keyboard
    )

# Добавляем обработчики callback-запросов
@dp.callback_query(lambda c: c.data == "motivation")
async def process_motivation_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    quote = await get_random_quote(callback_query.from_user.id)
    try:
        motivation_text = (
            "Мотивация — это ключ к успеху! Вот несколько советов, которые могут тебе помочь:\n"
            "- Постоянство в действиях — главная составляющая успеха.\n"
            "- Ставь конкретные цели и записывай их.\n"
            "- Не бойся неудач — каждый шаг в любом случае приближает тебя к успеху.\n\n"
            f"Цитата дня: {quote} 💫"
        )
        
        if callback_query.message.photo:
            await callback_query.message.delete()
            await callback_query.message.answer(motivation_text, reply_markup=main_keyboard)
        else:
            try:
                await callback_query.message.edit_text(motivation_text, reply_markup=main_keyboard)
            except Exception as e:
                if "message is not modified" not in str(e):
                    raise
                    
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error in motivation callback: {e}")
            await callback_query.message.answer(
                "Произошла ошибка. Попробуйте еще раз.",
                reply_markup=main_keyboard
            )

@dp.callback_query(lambda c: c.data == "workout")
async def process_workout_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        if callback_query.message.photo:
            await callback_query.message.delete()
            await callback_query.message.answer(
                "Выберите группу мышц для тренировки:",
                reply_markup=muscle_groups_keyboard
            )
        else:
            await callback_query.message.edit_text(
                "Выберите группу мышц для тренировки:",
                reply_markup=muscle_groups_keyboard
            )
    except Exception as e:
        logger.error(f"Error in workout callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=main_keyboard
        )

@dp.callback_query(lambda c: c.data == "health_tips")
async def process_health_tips_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        health_tips_text = (
            "Вот несколько простых и полезных советов для поддержания здоровья:\n"
            "- Пей достаточное количество воды каждый день (2-3 литра в зависимости от веса). 💧\n"
            "- Занимайся физической активностью хотя бы 30 минут в день. 🏃‍♂️\n"
            "- Спи не менее 7-8 часов — хороший сон способствует восстановлению организма. 😴\n"
            "- Следи за уровнем стресса и отдыхай, когда это необходимо. 🧘‍♀️\n"
            "- Не забывай про регулярные медицинские осмотры для предотвращения заболеваний. 🩺"
        )
        
        if callback_query.message.photo:
            # Если сообщение содержит фото, удаляем его и отправляем новое текстовое сообщение
            await callback_query.message.delete()
            await callback_query.message.answer(health_tips_text, reply_markup=main_keyboard)
        else:
            try:
                await callback_query.message.edit_text(health_tips_text, reply_markup=main_keyboard)
            except Exception as e:
                if "message is not modified" not in str(e):
                    raise  # Пробрасываем ошибку дальше, если это не ошибка о неизмененном сообщении
                
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error in health tips callback: {e}")
            await callback_query.message.answer(
                "Произошла ошибка. Попробуйте еще раз.",
                reply_markup=main_keyboard
            )

@dp.callback_query(lambda c: c.data == "progress")
async def process_progress_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        if callback_query.message.photo:
            await callback_query.message.delete()
            await callback_query.message.answer(
                "Меню отслеживания прогресса:",
                reply_markup=tracking_keyboard
            )
        else:
            await callback_query.message.edit_text(
                "Меню отслеживания прогресса:",
                reply_markup=tracking_keyboard
            )
    except Exception as e:
        logger.error(f"Error in progress callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=main_keyboard
        )

@dp.callback_query(lambda c: c.data == "recipes")
async def process_recipes_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        await callback_query.message.edit_text(
            "Выберите тип рецептов в зависимости от вашей цели: 🎯",
            reply_markup=recipes_keyboard
        )
    except Exception as e:
        logger.error(f"Error in recipes callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=main_keyboard
        )

@dp.callback_query(lambda c: c.data == "recipes_loss")
async def process_recipes_loss_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        await callback_query.message.edit_text(
            "Выберите рецепт для похудения: 🥗",
            reply_markup=weight_loss_keyboard
        )
    except Exception as e:
        logger.error(f"Error in recipes loss callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=recipes_keyboard
        )

@dp.callback_query(lambda c: c.data == "recipes_gain")
async def process_recipes_gain_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        await callback_query.message.edit_text(
            "Выберите рецепт для набора массы: 💪",
            reply_markup=weight_gain_keyboard
        )
    except Exception as e:
        logger.error(f"Error in recipes gain callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=recipes_keyboard
        )

@dp.callback_query(lambda c: c.data.startswith("recipe_"))
async def process_recipe_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        recipe_map = {
            "chicken_salad": "🥗 Салат с курицей",
            "fish": "🐟 Запеченная рыба с овощами",
            "avocado": "🥑 Авокадо-тост с яйцом",
            "veggie_soup": "🍲 Овощной суп",
            "steak": "🥩 Стейк с рисом",
            "smoothie": "🥜 Протеиновый смузи",
            "pasta": "🍗 Паста с курицей",
            "pancakes": "🥞 Протеиновые блины"
        }
        
        recipe_name = callback_query.data.replace("recipe_", "")
        if recipe_name in recipe_map:
            # Получаем последний записанный вес пользователя
            weight_record = await execute_db_query(
                """SELECT weight FROM weight_records 
                   WHERE user_id = ? 
                   ORDER BY date DESC LIMIT 1""",
                (callback_query.message.chat.id,),
                fetch=True
            )
            
            if not weight_record:
                await callback_query.message.edit_text(
                    "Пожалуйста, сначала введите ваш вес через меню 'Прогресс' -> '⚖️ Обновить вес'",
                    reply_markup=tracking_keyboard
                )
                return

            weight = weight_record[0][0]
            mapped_recipe_name = recipe_map[recipe_name]
            recipe = calculate_portions(weight, mapped_recipe_name)
            
            if recipe:
                recipe_text = f"{mapped_recipe_name}\n\nИнгредиенты (расчет на {weight} кг веса):\n"
                for ingredient, amount in recipe["ingredients"].items():
                    recipe_text += f"- {ingredient}: {amount} г\n"
                
                recipe_text += f"\nКалорийность порции: {recipe['calories']} ккал"
                recipe_text += f"\n\nПриготовление:\n{recipe['instructions']}"

                # Определяем тип клавиатуры на основе рецепта
                is_weight_loss = recipe_name in ["chicken_salad", "fish", "avocado", "veggie_soup"]
                keyboard = weight_loss_keyboard if is_weight_loss else weight_gain_keyboard

                recipe_images = {
                    "🥗 Салат с курицей": "https://i.imgur.com/ZeKqypn.jpeg",
                    "🐟 Запеченная рыба с овощами": "https://i.imgur.com/3sBXm68.jpg",
                    "🥑 Авокадо-тост с яйцом": "https://i.imgur.com/BADKEq0.jpg",
                    "🍲 Овощной суп": "https://i.imgur.com/Sx86Nvs.jpg",
                    "🥩 Стейк с рисом": "https://i.imgur.com/3pXM5nN.jpg",
                    "🥜 Протеиновый смузи": "https://i.imgur.com/N2dtgHZ.jpg",
                    "🍗 Паста с курицей": "https://i.imgur.com/DAAQd6O.jpg",
                    "🥞 Протеиновые блины": "https://i.imgur.com/THYuSsM.jpg"
                }

                try:
                    # Удаляем старое сообщение
                    await callback_query.message.delete()
                    
                    # Получаем URL фотографии
                    photo_url = recipe_images[mapped_recipe_name]
                    logger.info(f"Attempting to send photo for recipe {mapped_recipe_name} with URL {photo_url}")
                    
                    # Создаем новое сообщение с фото
                    new_message = await callback_query.message.answer_photo(
                        photo=photo_url,
                        caption=recipe_text,
                        reply_markup=keyboard
                    )
                    
                    logger.info(f"Successfully sent photo for recipe {mapped_recipe_name}")
                    
                except Exception as e:
                    logger.error(f"Error sending recipe photo for {mapped_recipe_name}: {str(e)}")
                    # Если не удалось отправить фото, отправляем только текст
                    await callback_query.message.answer(
                        f"⚠️ Не удалось загрузить фото рецепта.\n\n{recipe_text}",
                        reply_markup=keyboard
                    )
            else:
                await callback_query.message.edit_text(
                    "Извините, рецепт временно недоступен",
                    reply_markup=recipes_keyboard
                )
        else:
            await callback_query.message.edit_text(
                "Извините, рецепт не найден.",
                reply_markup=recipes_keyboard
            )
    except Exception as e:
        logger.error(f"Error in recipe callback: {str(e)}")
        await callback_query.message.answer(
            "Произошла ошибка при получении рецепта. Попробуйте позже.",
            reply_markup=recipes_keyboard
        )

@dp.callback_query(lambda c: c.data == "record_meal")
async def process_record_meal_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(UserStates.WAITING_FOR_MEAL)
    
    # Создаем текст с инструкциями и списком доступных продуктов
    products_text = "Доступные продукты и их калорийность (на 100г):\n"
    for food, calories in FOOD_CALORIES.items():
        products_text += f"• {food}: {calories} ккал\n"
    
    instructions = (
        "Введите информацию о приёме пищи в одном из форматов:\n"
        "1. [продукт] [граммы] (например: яблоко 100)\n"
        "2. [тип_приема_пищи] - [калории] (например: завтрак - 500)\n\n"
        f"{products_text}"
    )
    
    await callback_query.message.edit_text(
        instructions,
        reply_markup=cancel_keyboard
    )

@dp.callback_query(lambda c: c.data == "update_weight")
async def process_update_weight_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(UserStates.WAITING_FOR_WEIGHT)
    await callback_query.message.edit_text(
        "Введите ваш текущий вес в килограммах (например: 70.5)",
        reply_markup=cancel_keyboard
    )

@dp.callback_query(lambda c: c.data == "show_stats")
async def process_show_stats_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        await show_statistics(callback_query.message)
    except Exception as e:
        logger.error(f"Error in show stats callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка при показе статистики. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )

@dp.callback_query(lambda c: c.data == "set_calories")
async def process_set_calories_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(UserStates.WAITING_FOR_CALORIES)
    await callback_query.message.edit_text(
        "Введите вашу цель по калориям на день (например: 2000)",
        reply_markup=cancel_keyboard
    )

@dp.callback_query(lambda c: c.data == "cancel")
async def process_cancel_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await callback_query.message.edit_text(
            "Действие отменено.",
            reply_markup=main_keyboard
        )
    else:
        await callback_query.message.edit_text(
            "Нет активного действия для отмены.",
            reply_markup=main_keyboard
        )

@dp.callback_query(lambda c: c.data == "back_to_recipes")
async def process_back_to_recipes_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        if callback_query.message.photo:
            # Если текущее сообщение содержит фото, удаляем его и отправляем новое
            await callback_query.message.delete()
            await callback_query.message.answer(
                "Выберите тип рецептов в зависимости от вашей цели: 🎯",
                reply_markup=recipes_keyboard
            )
        else:
            # Если текущее сообщение без фото, просто редактируем его
            await callback_query.message.edit_text(
                "Выберите тип рецептов в зависимости от вашей цели: 🎯",
                reply_markup=recipes_keyboard
            )
    except Exception as e:
        logger.error(f"Error in back to recipes callback: {e}")
        # В случае ошибки отправляем новое сообщение
        await callback_query.message.answer(
            "Выберите тип рецептов в зависимости от вашей цели: 🎯",
            reply_markup=recipes_keyboard
        )

@dp.callback_query(lambda c: c.data == "back_to_main")
async def process_back_to_main_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "Вы вернулись в главное меню.",
        reply_markup=main_keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("muscles_"))
async def process_muscles_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        muscle_group_map = {
            "muscles_arms": "🦾 Руки",
            "muscles_legs": "🦵 Ноги",
            "muscles_chest": "🫁 Грудь",
            "muscles_back": "🔙 Спина",
            "muscles_shoulders": "🦴 Плечи",
            "muscles_abs": "💪 Пресс",
            "muscles_full": "🔄 Все тело"
        }
        
        muscle_group = muscle_group_map.get(callback_query.data)
        if not muscle_group:
            await callback_query.message.edit_text(
                "Извините, произошла ошибка. Попробуйте еще раз.",
                reply_markup=muscle_groups_keyboard
            )
            return
            
        all_plans = exercises[muscle_group]
        current_plan_index = last_shown_plan.get(muscle_group, -1)
        next_plan_index = (current_plan_index + 1) % len(all_plans)
        last_shown_plan[muscle_group] = next_plan_index
        
        workout = all_plans[next_plan_index]
        
        # Создаем клавиатуру для первого упражнения
        exercise_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Далее", callback_data=f"next_exercise_{muscle_group}_0")],
            [InlineKeyboardButton(text="🔙 Назад к выбору мышц", callback_data="workout")]
        ])
        
        # Удаляем старое сообщение
        await callback_query.message.delete()
        
        # Отправляем заголовок тренировки с первым упражнением
        exercise = workout[0]
        await callback_query.message.answer_photo(
            photo=exercise["image"],
            caption=f"🏋️‍♂️ План тренировки {next_plan_index + 1} для {muscle_group}:\n\n"
                   f"*{exercise['name']}*\n\n{exercise['description']}",
            reply_markup=exercise_keyboard,
            parse_mode="Markdown"
        )
            
    except Exception as e:
        logger.error(f"Error in muscles callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка при показе упражнений. Попробуйте позже.",
            reply_markup=muscle_groups_keyboard
        )

@dp.callback_query(lambda c: c.data.startswith("next_exercise_"))
async def process_next_exercise(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        # Получаем информацию из callback_data
        _, _, muscle_group, current_index = callback_query.data.split("_")
        current_index = int(current_index)
        
        # Получаем текущий план тренировок
        workout = exercises[muscle_group][last_shown_plan[muscle_group]]
        
        # Если это последнее упражнение, показываем рекомендации
        if current_index >= len(workout) - 1:
            recommendations = exercise_recommendations.get(muscle_group, {})
            if recommendations:
                tips_text = "\n".join(recommendations["tips"])
                technique_text = recommendations["technique"]
                
                recommendation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к выбору мышц", callback_data="workout")]
                ])
                
                await callback_query.message.edit_caption(
                    caption=f"🎯 Рекомендации для {muscle_group}:\n\n"
                           f"{tips_text}\n\n"
                           f"⚡️ Техника выполнения:\n"
                           f"{technique_text}",
                    reply_markup=recommendation_keyboard
                )
            return
        
        # Показываем следующее упражнение
        next_exercise = workout[current_index + 1]
        exercise_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Далее", callback_data=f"next_exercise_{muscle_group}_{current_index + 1}")],
            [InlineKeyboardButton(text="🔙 Назад к выбору мышц", callback_data="workout")]
        ])
        
        await callback_query.message.edit_media(
            media=types.InputMediaPhoto(
                media=next_exercise["image"],
                caption=f"*{next_exercise['name']}*\n\n{next_exercise['description']}",
                parse_mode="Markdown"
            ),
            reply_markup=exercise_keyboard
        )
            
    except Exception as e:
        logger.error(f"Error in next exercise callback: {e}")
        await callback_query.message.answer(
            "Произошла ошибка при показе упражнений. Попробуйте позже.",
            reply_markup=muscle_groups_keyboard
        )

@dp.callback_query(lambda c: c.data == "manage_reminders")
async def process_manage_reminders_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        # Получаем текущие напоминания пользователя
        reminders = await execute_db_query(
            "SELECT id, reminder_type, reminder_time, days FROM reminders WHERE user_id = ? AND is_active = TRUE",
            (callback_query.from_user.id,),
            fetch=True
        )
        
        text = "⏰ Управление напоминаниями\n\n"
        
        if reminders:
            text += "Ваши текущие напоминания:\n"
            for r in reminders:
                reminder_id, r_type, r_time, days = r
                type_emoji = "🏋️" if r_type == "workout" else "🍽"
                days_text = days.replace(",", ", ")
                text += f"{type_emoji} {r_type.capitalize()}: {r_time} ({days_text})\n"
        else:
            text += "У вас пока нет активных напоминаний.\n"
        
        reminder_management_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить напоминание", callback_data="add_reminder")],
            [InlineKeyboardButton(text="➖ Удалить напоминание", callback_data="delete_reminder")] if reminders else [],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_tracking")]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=reminder_management_keyboard)
        
    except Exception as e:
        logger.error(f"Error in manage reminders: {e}")
        await callback_query.message.answer(
            "Произошла ошибка при управлении напоминаниями. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )

@dp.callback_query(lambda c: c.data == "add_reminder")
async def process_add_reminder_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(UserStates.WAITING_FOR_REMINDER_TYPE)
    await callback_query.message.edit_text(
        "Выберите тип напоминания:",
        reply_markup=reminder_type_keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("reminder_"))
async def process_reminder_type_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    reminder_type = callback_query.data.replace("reminder_", "")
    await state.update_data(reminder_type=reminder_type)
    await state.set_state(UserStates.WAITING_FOR_REMINDER_TIME)
    
    time_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="07:00", callback_data="time_07:00"),
            InlineKeyboardButton(text="08:00", callback_data="time_08:00"),
            InlineKeyboardButton(text="09:00", callback_data="time_09:00")
        ],
        [
            InlineKeyboardButton(text="12:00", callback_data="time_12:00"),
            InlineKeyboardButton(text="13:00", callback_data="time_13:00"),
            InlineKeyboardButton(text="14:00", callback_data="time_14:00")
        ],
        [
            InlineKeyboardButton(text="18:00", callback_data="time_18:00"),
            InlineKeyboardButton(text="19:00", callback_data="time_19:00"),
            InlineKeyboardButton(text="20:00", callback_data="time_20:00")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    
    await callback_query.message.edit_text(
        "Выберите время для напоминания:",
        reply_markup=time_keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("time_"))
async def process_reminder_time_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    reminder_time = callback_query.data.replace("time_", "")
    await state.update_data(reminder_time=reminder_time)
    await state.set_state(UserStates.WAITING_FOR_REMINDER_DAYS)
    
    days_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пн", callback_data="days_mon"),
            InlineKeyboardButton(text="Вт", callback_data="days_tue"),
            InlineKeyboardButton(text="Ср", callback_data="days_wed")
        ],
        [
            InlineKeyboardButton(text="Чт", callback_data="days_thu"),
            InlineKeyboardButton(text="Пт", callback_data="days_fri"),
            InlineKeyboardButton(text="Сб", callback_data="days_sat")
        ],
        [
            InlineKeyboardButton(text="Вс", callback_data="days_sun"),
            InlineKeyboardButton(text="Все дни", callback_data="days_all")
        ],
        [InlineKeyboardButton(text="✅ Готово", callback_data="days_done")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    
    await callback_query.message.edit_text(
        "Выберите дни для напоминания (можно выбрать несколько):",
        reply_markup=days_keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("days_"))
async def process_reminder_days_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    if callback_query.data == "days_done":
        user_data = await state.get_data()
        if "selected_days" not in user_data or not user_data["selected_days"]:
            await callback_query.message.edit_text(
                "Пожалуйста, выберите хотя бы один день для напоминания.",
                reply_markup=callback_query.message.reply_markup
            )
            return
            
        # Сохраняем напоминание в базу данных
        reminder_type = user_data["reminder_type"]
        reminder_time = user_data["reminder_time"]
        days = ",".join(user_data["selected_days"])
        
        await execute_db_query(
            """INSERT INTO reminders (user_id, reminder_type, reminder_time, days) 
               VALUES (?, ?, ?, ?)""",
            (callback_query.from_user.id, reminder_type, reminder_time, days)
        )
        
        await state.clear()
        await callback_query.message.edit_text(
            "✅ Напоминание успешно установлено!",
            reply_markup=tracking_keyboard
        )
        return
        
    if callback_query.data == "days_all":
        all_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        await state.update_data(selected_days=all_days)
        await callback_query.message.edit_text(
            "Выбраны все дни недели. Нажмите '✅ Готово' для сохранения.",
            reply_markup=callback_query.message.reply_markup
        )
        return
        
    day = callback_query.data.replace("days_", "")
    day_map = {
        "mon": "Пн", "tue": "Вт", "wed": "Ср",
        "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс"
    }
    
    if day in day_map:
        user_data = await state.get_data()
        selected_days = user_data.get("selected_days", [])
        day_name = day_map[day]
        
        if day_name not in selected_days:
            selected_days.append(day_name)
        else:
            selected_days.remove(day_name)
            
        await state.update_data(selected_days=selected_days)
        
        days_text = ", ".join(selected_days) if selected_days else "Не выбрано"
        await callback_query.message.edit_text(
            f"Выбранные дни: {days_text}\n\nВыберите дни для напоминания (можно выбрать несколько):",
            reply_markup=callback_query.message.reply_markup
        )

@dp.callback_query(lambda c: c.data == "delete_reminder")
async def process_delete_reminder_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        reminders = await execute_db_query(
            "SELECT id, reminder_type, reminder_time, days FROM reminders WHERE user_id = ? AND is_active = TRUE",
            (callback_query.from_user.id,),
            fetch=True
        )
        
        if not reminders:
            await callback_query.message.edit_text(
                "У вас нет активных напоминаний.",
                reply_markup=tracking_keyboard
            )
            return
            
        keyboard = []
        for reminder in reminders:
            reminder_id, r_type, r_time, days = reminder
            type_emoji = "🏋️" if r_type == "workout" else "🍽"
            days_text = days.replace(",", ", ")
            text = f"{type_emoji} {r_type.capitalize()}: {r_time} ({days_text})"
            keyboard.append([InlineKeyboardButton(
                text=f"❌ {text}",
                callback_data=f"del_reminder_{reminder_id}"
            )])
            
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="manage_reminders")])
        delete_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback_query.message.edit_text(
            "Выберите напоминание для удаления:",
            reply_markup=delete_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in delete reminder: {e}")
        await callback_query.message.answer(
            "Произошла ошибка при удалении напоминания. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )

@dp.callback_query(lambda c: c.data.startswith("del_reminder_"))
async def process_delete_specific_reminder_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    try:
        reminder_id = int(callback_query.data.replace("del_reminder_", ""))
        await execute_db_query(
            "UPDATE reminders SET is_active = FALSE WHERE id = ? AND user_id = ?",
            (reminder_id, callback_query.from_user.id)
        )
        
        await callback_query.message.edit_text(
            "✅ Напоминание успешно удалено!",
            reply_markup=tracking_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in delete specific reminder: {e}")
        await callback_query.message.answer(
            "Произошла ошибка при удалении напоминания. Попробуйте позже.",
            reply_markup=tracking_keyboard
        )

@dp.callback_query(lambda c: c.data == "back_to_tracking")
async def process_back_to_tracking_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "Меню отслеживания прогресса:",
        reply_markup=tracking_keyboard
    )

async def send_reminder(user_id: int, reminder_type: str):
    try:
        messages = {
            "workout": [
                "🏋️ Время тренировки! Готовы покорять новые вершины?",
                "💪 Пора размяться и зарядиться энергией!",
                "🎯 Ваша тренировка ждет вас. Вперед к целям!",
                "⚡️ Время становиться сильнее! Тренировка начинается.",
                "🔥 Готовы к продуктивной тренировке?"
            ],
            "meal": [
                "🍽 Время приема пищи! Не забудьте про правильное питание.",
                "🥗 Пора подкрепиться! Помните о балансе в питании.",
                "⏰ Время перекусить! Выбирайте полезные продукты.",
                "🍳 Не пропускайте прием пищи - это важно для здоровья!",
                "🥑 Время для здорового питания!"
            ]
        }
        
        message = random.choice(messages[reminder_type])
        await bot.send_message(user_id, message)
        
    except Exception as e:
        logger.error(f"Error sending reminder to user {user_id}: {e}")

async def check_reminders():
    while True:
        try:
            current_time = datetime.now()
            current_weekday = current_time.strftime("%a").lower()
            time_str = current_time.strftime("%H:%M")
            
            # Получаем все активные напоминания для текущего времени
            reminders = await execute_db_query(
                """SELECT user_id, reminder_type FROM reminders 
                   WHERE reminder_time = ? AND is_active = TRUE""",
                (time_str,),
                fetch=True
            )
            
            if reminders:
                for reminder in reminders:
                    user_id, reminder_type = reminder
                    await send_reminder(user_id, reminder_type)
            
            # Ждем до следующей минуты
            next_minute = (current_time + timedelta(minutes=1)).replace(second=0, microsecond=0)
            await asyncio.sleep((next_minute - current_time).total_seconds())
            
        except Exception as e:
            logger.error(f"Error in check_reminders: {e}")
            await asyncio.sleep(60)

async def main():
    try:
        global bot
        logger.info("Starting bot...")
        
        # Создаем сессию с базовыми настройками
        session = AiohttpSession()
        
        # Инициализируем бота с созданной сессией
        bot = Bot(token=TOKEN, session=session)
        
        await init_db()
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем проверку напоминаний в фоновом режиме
        asyncio.create_task(check_reminders())
        
        # Добавляем обработку ошибок при получении обновлений
        while True:
            try:
                await dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    close_bot_session=True
                )
            except Exception as e:
                logger.error(f"Polling error: {e}")
                # Ждем 5 секунд перед повторной попыткой
                await asyncio.sleep(5)
                continue
                
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
    finally:
        logger.info("Bot stopped")
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
