import aiosqlite
from datetime import datetime

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_name: str = "fitness_bot.db"):
        self.db_name = db_name
    
    async def create_tables(self):
        """Создание необходимых таблиц"""
        async with aiosqlite.connect(self.db_name) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица тренировок
            await db.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    workout_type TEXT,
                    duration INTEGER,
                    calories_burned INTEGER,
                    exercises_completed INTEGER,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица записей веса
            await db.execute("""
                CREATE TABLE IF NOT EXISTS weight_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    weight REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица измерений тела
            await db.execute("""
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chest REAL,
                    waist REAL,
                    hips REAL,
                    biceps REAL,
                    thighs REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица напоминаний о тренировках
            await db.execute("""
                CREATE TABLE IF NOT EXISTS workout_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    time TEXT,
                    days TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица напоминаний о питании
            await db.execute("""
                CREATE TABLE IF NOT EXISTS meal_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    meal_count INTEGER,
                    meal_times TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица дневника питания
            await db.execute("""
                CREATE TABLE IF NOT EXISTS meal_diary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    meal_name TEXT,
                    calories REAL,
                    proteins REAL,
                    fats REAL,
                    carbs REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
    
    async def add_user(self, user_id: int, username: str = None):
        """Добавление нового пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            await db.commit()
    
    async def save_workout(self, user_id: int, workout_type: str, duration: int,
                          calories_burned: int, exercises_completed: int):
        """Сохранение информации о завершенной тренировке"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                """
                INSERT INTO workouts 
                (user_id, workout_type, duration, calories_burned, exercises_completed)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, workout_type, duration, calories_burned, exercises_completed)
            )
            await db.commit()
    
    async def record_weight(self, user_id: int, weight: float):
        """Запись веса пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO weight_records (user_id, weight) VALUES (?, ?)",
                (user_id, weight)
            )
            await db.commit()
    
    async def record_measurements(self, user_id: int, chest: float, waist: float,
                                hips: float, biceps: float, thighs: float):
        """Запись измерений тела"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                """
                INSERT INTO measurements 
                (user_id, chest, waist, hips, biceps, thighs)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, chest, waist, hips, biceps, thighs)
            )
            await db.commit()
    
    async def get_user_statistics(self, user_id: int) -> tuple:
        """Получение общей статистики пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                """
                SELECT 
                    COUNT(*) as total_workouts,
                    SUM(duration) as total_duration,
                    SUM(calories_burned) as total_calories,
                    SUM(exercises_completed) as total_exercises
                FROM workouts
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                return await cursor.fetchone()
    
    async def get_weight_history(self, user_id: int) -> list:
        """Получение истории изменения веса"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                """
                SELECT weight, recorded_at
                FROM weight_records
                WHERE user_id = ?
                ORDER BY recorded_at DESC
                LIMIT 10
                """,
                (user_id,)
            ) as cursor:
                return await cursor.fetchall()
    
    async def get_measurements_history(self, user_id: int) -> list:
        """Получение истории измерений"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                """
                SELECT chest, waist, hips, biceps, thighs, recorded_at
                FROM measurements
                WHERE user_id = ?
                ORDER BY recorded_at DESC
                LIMIT 5
                """,
                (user_id,)
            ) as cursor:
                return await cursor.fetchall()
    
    async def get_recent_workouts(self, user_id: int, limit: int = 5) -> list:
        """Получение последних тренировок пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                """
                SELECT workout_type, duration, calories_burned, completed_at
                FROM workouts
                WHERE user_id = ?
                ORDER BY completed_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            ) as cursor:
                return await cursor.fetchall()
    
    async def save_workout_reminder(self, user_id: int, time: str, days: str):
        """Сохранение напоминания о тренировках"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                """
                INSERT INTO workout_reminders (user_id, time, days)
                VALUES (?, ?, ?)
                """,
                (user_id, time, days)
            )
            await db.commit()
    
    async def save_meal_reminder(self, user_id: int, meal_count: int, meal_times: str):
        """Сохранение напоминания о питании"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                """
                INSERT INTO meal_reminders (user_id, meal_count, meal_times)
                VALUES (?, ?, ?)
                """,
                (user_id, meal_count, meal_times)
            )
            await db.commit()
    
    async def get_workout_reminders(self, user_id: int) -> tuple:
        """Получение напоминаний о тренировках"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                """
                SELECT time, days
                FROM workout_reminders
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,)
            ) as cursor:
                return await cursor.fetchone()
    
    async def get_meal_reminders(self, user_id: int) -> tuple:
        """Получение напоминаний о питании"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                """
                SELECT meal_count, meal_times
                FROM meal_reminders
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,)
            ) as cursor:
                return await cursor.fetchone() 