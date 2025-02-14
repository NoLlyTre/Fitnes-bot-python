from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import WORKOUT_TYPES
from workout_manager import WorkoutSession

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создание главной клавиатуры"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🏋️ Тренировки", callback_data="menu_workouts"))
    builder.add(InlineKeyboardButton(text="📊 Прогресс", callback_data="menu_progress"))
    builder.add(InlineKeyboardButton(text="🍳 Питание", callback_data="menu_nutrition"))
    builder.add(InlineKeyboardButton(text="⏰ Напоминания", callback_data="menu_reminders"))
    builder.add(InlineKeyboardButton(text="💡 Советы", callback_data="menu_tips"))
    
    builder.adjust(2)
    return builder.as_markup()

def get_workouts_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора тренировки"""
    builder = InlineKeyboardBuilder()
    
    for key, value in WORKOUT_TYPES.items():
        builder.add(InlineKeyboardButton(text=value, callback_data=key))
    
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main"))
    builder.adjust(2, 1)
    return builder.as_markup()

def get_progress_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для раздела прогресса"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="⚖️ Записать вес", callback_data="record_weight"))
    builder.add(InlineKeyboardButton(text="📏 Записать измерения", callback_data="record_measurements"))
    builder.add(InlineKeyboardButton(text="📊 Показать статистику", callback_data="show_statistics"))
    builder.add(InlineKeyboardButton(text="📈 Показать прогресс", callback_data="show_progress"))
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main"))
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_nutrition_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для раздела питания"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🥗 Рецепты", callback_data="nutrition_recipes"))
    builder.add(InlineKeyboardButton(text="🔢 Калькулятор калорий", callback_data="nutrition_calculator"))
    builder.add(InlineKeyboardButton(text="📝 Дневник питания", callback_data="nutrition_diary"))
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main"))
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_reminders_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для раздела напоминаний"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🏋️ Напоминания о тренировках", callback_data="workout_reminders"))
    builder.add(InlineKeyboardButton(text="🍽 Напоминания о питании", callback_data="meal_reminders"))
    builder.add(InlineKeyboardButton(text="⚙️ Настройки напоминаний", callback_data="reminder_settings"))
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main"))
    
    builder.adjust(1)
    return builder.as_markup()

def get_tips_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для раздела советов"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🏋️ Советы по тренировкам", callback_data="tips_workout"))
    builder.add(InlineKeyboardButton(text="🥗 Советы по питанию", callback_data="tips_nutrition"))
    builder.add(InlineKeyboardButton(text="💪 Мотивация", callback_data="tips_motivation"))
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main"))
    
    builder.adjust(1)
    return builder.as_markup()

def get_exercise_keyboard(session: WorkoutSession) -> InlineKeyboardMarkup:
    """Создание клавиатуры для управления тренировкой"""
    builder = InlineKeyboardBuilder()
    
    if session.current_exercise > 0:
        builder.add(InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_exercise"))
    
    if session.current_exercise < len(session.exercises) - 1:
        builder.add(InlineKeyboardButton(text="➡️ Следующее", callback_data="next_exercise"))
    
    builder.add(InlineKeyboardButton(text="❌ Завершить", callback_data="end_workout"))
    builder.adjust(2)
    return builder.as_markup() 