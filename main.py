import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import sqlite3
import datetime
import plotly.graph_objects as go
import io
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging.handlers
import sys
from aiogram import BaseMiddleware
from collections import defaultdict
import time
import random

TOKEN = "7997378459:AAE4Sd0D-Sjbf-bvEfub7cHeVSIStKLMjuc"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройка расширенного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            'bot.log',
            maxBytes=10485760,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger(__name__)

# Создаем пул соединений с базой данных
class DatabasePool:
    def __init__(self, database_name: str):
        self.database_name = database_name
        self._pool = []
        self.max_connections = 10
        
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        if not self._pool:
            conn = await aiosqlite.connect(self.database_name)
            await conn.execute("PRAGMA journal_mode=WAL")  # Включаем WAL режим для лучшей производительности
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

# Создаем экземпляр пула
db_pool = DatabasePool('fitness_bot.db')

# Функция для безопасного выполнения SQL-запросов
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

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💪 Мотивация")],
        [KeyboardButton(text="🥗 Диета")],
        [KeyboardButton(text="💡 Советы по здоровью")],
        [KeyboardButton(text="📈 Прогресс")],
        [KeyboardButton(text="🍴 Рецепты")]
    ],
    resize_keyboard=True
)

recipes_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔻 Рецепты для похудения")],
        [KeyboardButton(text="🔺 Рецепты для набора массы")],
        [KeyboardButton(text="🔙 Назад в меню")],
    ],
    resize_keyboard=True
)

weight_loss_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🥗 Салат с курицей")],
        [KeyboardButton(text="🐟 Запеченная рыба с овощами")],
        [KeyboardButton(text="🥑 Авокадо-тост с яйцом")],
        [KeyboardButton(text="🍲 Овощной суп")],
        [KeyboardButton(text="🔙 Назад к выбору типа")],
    ],
    resize_keyboard=True
)

weight_gain_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🥩 Стейк с рисом")],
        [KeyboardButton(text="🥜 Протеиновый смузи")],
        [KeyboardButton(text="🍗 Паста с курицей")],
        [KeyboardButton(text="🥞 Протеиновые блины")],
        [KeyboardButton(text="🔙 Назад к выбору типа")],
    ],
    resize_keyboard=True
)

tracking_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Записать приём пищи")],
        [KeyboardButton(text="⚖️ Обновить вес")],
        [KeyboardButton(text="📊 Показать статистику")],
        [KeyboardButton(text="🎯 Установить цель калорий")],
        [KeyboardButton(text="🔙 Назад в меню")],
    ],
    resize_keyboard=True
)

# Добавим новые клавиатуры с кнопкой отмены
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

# Middleware для ограничения частоты запросов
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=1):
        self.rate_limit = rate_limit
        self.users = defaultdict(lambda: {"last_request": 0, "request_count": 0})
        
    async def __call__(self, handler, event: types.Message, data):
        user_id = event.from_user.id
        current_time = time.time()
        user_data = self.users[user_id]
        
        # Сброс счетчика если прошло больше секунды
        if current_time - user_data["last_request"] > 1:
            user_data["request_count"] = 0
            
        user_data["request_count"] += 1
        user_data["last_request"] = current_time
        
        if user_data["request_count"] > self.rate_limit:
            await event.answer("Пожалуйста, подождите немного перед следующим запросом.")
            return
            
        return await handler(event, data)

# Регистрируем middleware
dp.message.middleware(ThrottlingMiddleware())

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я твой фитнес-бот. Вот что я могу:\n"
        "1. 💪 Мотивация — вдохновляющие цитаты.\n"
        "2. 🥗 Диета — советы по отслеживанию рациона.\n"
        "3. 💡 Советы по здоровью — полезные рекомендации.\n"
        "4. 📈 Прогресс — как отслеживать достижения.\n"
        "5. 🍴 Рецепты — здоровые и вкусные блюда.",
        reply_markup=keyboard
    )

# Функция для получения случайной цитаты
async def get_random_quote() -> str:
    try:
        with open('quotes.txt', 'r', encoding='utf-8') as file:
            quotes = file.readlines()
        # Удаляем пустые строки и пробелы
        quotes = [quote.strip() for quote in quotes if quote.strip()]
        return random.choice(quotes)
    except Exception as e:
        logger.error(f"Error reading quotes file: {e}")
        return "\"Самый трудный шаг — это начало, все остальное проще!\""

# Обновляем обработчик мотивации
@dp.message(lambda message: message.text == "💪 Мотивация")
async def send_motivation(message: types.Message):
    try:
        quote = await get_random_quote()
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

@dp.message(lambda message: message.text == "🥗 Диета")
async def send_diet(message: types.Message):
    await message.answer(
        "Диета — это не временные ограничения, а способ поддержания здоровья и энергии.\n"
        "Вот несколько советов для здорового питания:\n"
        "- Разделяй прием пищи на 5-6 небольших приемов пищи в течение дня.\n"
        "- Пей много воды — это способствует метаболизму и улучшает пищеварение. 💧\n"
        "- Включай в рацион больше овощей и фруктов. 🍎🥦\n"
        "- Ограничь потребление сахара и простых углеводов. 🚫🍬\n"
        "Запомни, что здоровая диета — это не диета на неделю, а образ жизни! 🥑"
    )

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

def calculate_portions(weight: float, recipe_type: str) -> dict:
    """Рассчитывает порции ингредиентов на основе веса пользователя"""
    base_weight = 70  # базовый вес для расчета
    multiplier = weight / base_weight
    
    recipes = {
        "🥗 Салат с курицей": {
            "base": {
                "Куриная грудка": 150,
                "Листья салата": 50,
                "Помидоры": 100,
                "Огурцы": 100,
                "Оливковое масло": 15
            },
            "calories_per_100g": 120,
            "instructions": "1. Отварите куриную грудку\n2. Нарежьте все ингредиенты\n3. Заправьте оливковым маслом"
        },
        "🥩 Стейк с рисом": {
            "base": {
                "Говяжий стейк": 200,
                "Рис": 150,
                "Овощи": 100,
                "Оливковое масло": 20
            },
            "calories_per_100g": 250,
            "instructions": "1. Приготовьте рис\n2. Обжарьте стейк до желаемой прожарки\n3. Подавайте с овощами"
        }
    }
    
    if recipe_type not in recipes:
        return None
        
    recipe = recipes[recipe_type]
    result = {
        "ingredients": {},
        "calories": 0,
        "instructions": recipe["instructions"]
    }
    
    for ingredient, amount in recipe["base"].items():
        adjusted_amount = round(amount * multiplier)
        result["ingredients"][ingredient] = adjusted_amount
    
    total_weight = sum(result["ingredients"].values())
    result["calories"] = round(total_weight * recipe["calories_per_100g"] / 100)
    
    return result

@dp.message(lambda message: message.text in ["🥗 Салат с курицей", "🥩 Стейк с рисом"])
async def send_recipe_details(message: types.Message):
    try:
        # Получаем вес пользователя из базы данных
        weight_record = await execute_db_query(
            """SELECT weight FROM weight_records 
               WHERE user_id = ? 
               ORDER BY date DESC LIMIT 1""",
            (message.from_user.id,),
            fetch=True
        )
        
        if not weight_record:
            await message.answer(
                "Пожалуйста, сначала введите ваш вес через меню 'Прогресс' -> '⚖️ Обновить вес'"
            )
            return
            
        weight = weight_record[0][0]
        recipe = calculate_portions(weight, message.text)
        
        if not recipe:
            await message.answer("Извините, рецепт временно недоступен")
            return
            
        # Формируем текст рецепта
        recipe_text = f"{message.text}\n\nИнгредиенты (расчет на {weight} кг веса):\n"
        for ingredient, amount in recipe["ingredients"].items():
            recipe_text += f"- {ingredient}: {amount} г\n"
        
        recipe_text += f"\nКалорийность порции: {recipe['calories']} ккал"
        
        if "Салат" in message.text:
            recipe_text += "\n\nПриготовление:\n" + recipe["instructions"]
        elif "Стейк" in message.text:
            recipe_text += "\n\nПриготовление:\n" + recipe["instructions"]
        
        await message.answer(recipe_text)
    except Exception as e:
        logger.error(f"Error in send_recipe_details for user {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при получении рецепта. Попробуйте позже.")

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
        await message.answer("Действие отменено.", reply_markup=keyboard)
    else:
        await message.answer("Нет активного действия для отмены.", reply_markup=keyboard)

@dp.message(lambda message: message.text == "📝 Записать приём пищи")
async def record_meal(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.WAITING_FOR_MEAL)
    await message.answer(
        "Введите информацию о приёме пищи в формате:\n"
        "Тип приёма пищи (завтрак/обед/ужин/перекус) - калории\n"
        "Например: завтрак - 500\n\n"
        "Для отмены нажмите кнопку ❌ Отмена",
        reply_markup=cancel_keyboard
    )

@dp.message(UserStates.WAITING_FOR_MEAL)
async def process_meal(message: types.Message, state: FSMContext):
    try:
        meal_type, calories = message.text.split('-')
        meal_type = meal_type.strip().lower()
        calories = int(calories.strip())
        
        await execute_db_query(
            "INSERT INTO meal_records (user_id, meal_type, calories, date) VALUES (?, ?, ?, ?)",
            (message.from_user.id, meal_type, calories, datetime.datetime.now().strftime('%Y-%m-%d'))
        )
        
        await message.answer("Приём пищи успешно записан! 📝", reply_markup=tracking_keyboard)
        await state.clear()
    except ValueError:
        await message.answer(
            "Неверный формат. Введите в формате: завтрак - 500\n"
            "Или нажмите ❌ Отмена для отмены действия",
            reply_markup=cancel_keyboard
        )
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

        await execute_db_query(
            "INSERT INTO weight_records (user_id, weight, date) VALUES (?, ?, ?)",
            (message.from_user.id, weight, datetime.datetime.now().strftime('%Y-%m-%d'))
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
        # Получаем цель по калориям
        target_result = await execute_db_query(
            "SELECT target_calories FROM users WHERE user_id = ?",
            (message.from_user.id,),
            fetch=True
        )
        target_calories = target_result[0][0] if target_result else 2000

        # Получаем статистику калорий
        calories_data = await execute_db_query(
            """SELECT date, SUM(calories) 
               FROM meal_records 
               WHERE user_id = ? AND date >= date('now', '-7 days')
               GROUP BY date ORDER BY date""",
            (message.from_user.id,),
            fetch=True
        )
        
        dates = [row[0] for row in calories_data]
        calories = [row[1] for row in calories_data]

        # Получаем статистику веса
        weight_data = await execute_db_query(
            """SELECT date, weight
               FROM weight_records
               WHERE user_id = ?
               AND date >= date('now', '-7 days')
               ORDER BY date""",
            (message.from_user.id,),
            fetch=True
        )
        
        weight_dates = [row[0] for row in weight_data]
        weights = [row[1] for row in weight_data]
        
        if not dates and not weight_dates:
            await message.answer("Нет данных для отображения статистики.")
            return

        # Создаем график с двумя осями Y
        fig = go.Figure()

        if dates:
            # График калорий
            fig.add_trace(go.Scatter(
                x=dates,
                y=calories,
                mode='lines+markers',
                name='Калории',
                line=dict(color='blue')
            ))
            
            # Добавляем линию цели
            fig.add_hline(
                y=target_calories,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Цель: {target_calories} ккал"
            )

        if weight_dates:
            # График веса
            fig.add_trace(go.Scatter(
                x=weight_dates,
                y=weights,
                mode='lines+markers',
                name='Вес (кг)',
                yaxis='y2',
                line=dict(color='green')
            ))

        fig.update_layout(
            title='Статистика за последние 7 дней',
            xaxis_title='Дата',
            yaxis_title='Калории',
            yaxis2=dict(
                title='Вес (кг)',
                overlaying='y',
                side='right'
            ),
            template='plotly_white'
        )

        img_bytes = fig.to_image(format="png")
        buf = io.BytesIO(img_bytes)
        buf.seek(0)  # Убедимся, что указатель в начале файла
        
        # Создаем InputFile из буфера
        input_file = types.BufferedInputFile(
            buf.getvalue(),
            filename="statistics.png"
        )
        
        # Формируем текстовый отчет
        report = "📊 Статистика за последнюю неделю:\n\n"
        
        if dates:
            avg_calories = sum(calories) / len(calories)
            report += f"Среднее потребление калорий: {int(avg_calories)} ккал\n"
            report += f"Цель калорий: {target_calories} ккал\n"
        
        if weight_dates:
            latest_weight = weights[-1]
            first_weight = weights[0]
            weight_diff = latest_weight - first_weight
            report += f"\nТекущий вес: {latest_weight} кг\n"
            if weight_diff != 0:
                report += f"Изменение веса за период: {weight_diff:+.1f} кг"

        await message.answer_photo(input_file, caption=report)
        
    except Exception as e:
        logger.error(f"Error in show_statistics for user {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при создании статистики. Попробуйте позже.")

@dp.message(lambda message: message.text == "🔙 Назад в меню")
async def back_to_main_menu(message: types.Message):
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text in [
    "🐟 Запеченная рыба с овощами",
    "🥑 Авокадо-тост с яйцом",
    "🍲 Овощной суп",
    "🥜 Протеиновый смузи",
    "🍗 Паста с курицей",
    "🥞 Протеиновые блины"
])
async def send_other_recipe_details(message: types.Message):
    # Добавляем новые рецепты в словарь
    recipes = {
        "🐟 Запеченная рыба с овощами": {
            "base": {
                "Рыба (филе)": 200,
                "Брокколи": 100,
                "Морковь": 100,
                "Лимон": 30,
                "Оливковое масло": 15
            },
            "calories_per_100g": 130,
            "instructions": "1. Подготовьте филе рыбы\n2. Нарежьте овощи\n3. Запекайте 20-25 минут при 180°C"
        },
        "🥑 Авокадо-тост с яйцом": {
            "base": {
                "Авокадо": 100,
                "Цельнозерновой хлеб": 60,
                "Яйцо": 60,
                "Помидоры черри": 50,
                "Зелень": 10
            },
            "calories_per_100g": 220,
            "instructions": "1. Поджарьте хлеб\n2. Разомните авокадо\n3. Приготовьте яйцо пашот\n4. Соберите тост"
        },
        "🍲 Овощной суп": {
            "base": {
                "Морковь": 100,
                "Картофель": 150,
                "Лук": 50,
                "Сельдерей": 50,
                "Зелень": 20
            },
            "calories_per_100g": 45,
            "instructions": "1. Нарежьте овощи\n2. Варите 30 минут\n3. Добавьте зелень перед подачей"
        },
        "🥜 Протеиновый смузи": {
            "base": {
                "Банан": 120,
                "Протеин": 30,
                "Молоко": 250,
                "Арахисовая паста": 30,
                "Овсянка": 30
            },
            "calories_per_100g": 150,
            "instructions": "1. Смешайте все ингредиенты\n2. Взбейте в блендере\n3. Подавайте сразу"
        },
        "🍗 Паста с курицей": {
            "base": {
                "Паста цельнозерновая": 100,
                "Куриная грудка": 200,
                "Томатный соус": 100,
                "Пармезан": 30,
                "Базилик": 10
            },
            "calories_per_100g": 180,
            "instructions": "1. Отварите пасту\n2. Приготовьте курицу\n3. Смешайте с соусом"
        },
        "🥞 Протеиновые блины": {
            "base": {
                "Овсяная мука": 100,
                "Протеин": 30,
                "Яйцо": 60,
                "Молоко": 200,
                "Мед": 20
            },
            "calories_per_100g": 200,
            "instructions": "1. Смешайте все ингредиенты\n2. Выпекайте на сковороде\n3. Подавайте с медом"
        }
    }
    
    try:
        # Получаем вес пользователя
        weight_record = await execute_db_query(
            """SELECT weight FROM weight_records 
               WHERE user_id = ? 
               ORDER BY date DESC LIMIT 1""",
            (message.from_user.id,),
            fetch=True
        )
        
        if not weight_record:
            await message.answer(
                "Пожалуйста, сначала введите ваш вес через меню 'Прогресс' -> '⚖️ Обновить вес'"
            )
            return
            
        weight = weight_record[0][0]
        recipe = recipes.get(message.text)
        
        if not recipe:
            await message.answer("Извините, рецепт временно недоступен")
            return
            
        # Рассчитываем порции
        multiplier = weight / 70  # базовый вес 70 кг
        adjusted_ingredients = {
            ingredient: round(amount * multiplier)
            for ingredient, amount in recipe["base"].items()
        }
        
        total_weight = sum(adjusted_ingredients.values())
        total_calories = round(total_weight * recipe["calories_per_100g"] / 100)
        
        # Формируем текст рецепта
        recipe_text = f"{message.text}\n\nИнгредиенты (расчет на {weight} кг веса):\n"
        for ingredient, amount in adjusted_ingredients.items():
            recipe_text += f"- {ingredient}: {amount} г\n"
        
        recipe_text += f"\nКалорийность порции: {total_calories} ккал"
        recipe_text += f"\n\nПриготовление:\n{recipe['instructions']}"
        
        await message.answer(recipe_text)
        
    except Exception as e:
        logger.error(f"Error in send_other_recipe_details for user {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при получении рецепта. Попробуйте позже.")

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
        'CREATE INDEX IF NOT EXISTS idx_weight_records_user_date ON weight_records(user_id, date)',
        'CREATE INDEX IF NOT EXISTS idx_meal_records_user_date ON meal_records(user_id, date)'
    ]
    
    for query in queries:
        await execute_db_query(query)

async def main():
    try:
        logger.info("Starting bot...")
        await init_db()
        
        # Настраиваем повторные попытки для webhook
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем бота с обработкой ошибок
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=True
        )
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
    finally:
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
