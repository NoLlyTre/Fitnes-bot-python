from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    """Состояния пользователя для FSM"""
    waiting_for_weight = State()        # Ожидание ввода веса
    waiting_for_chest = State()         # Ожидание ввода обхвата груди
    waiting_for_waist = State()         # Ожидание ввода обхвата талии
    waiting_for_hips = State()          # Ожидание ввода обхвата бедер
    waiting_for_biceps = State()        # Ожидание ввода обхвата бицепса
    waiting_for_thighs = State()        # Ожидание ввода обхвата бедра
    
    # Состояния для напоминаний
    setting_workout_time = State()      # Установка времени напоминания о тренировке
    setting_workout_days = State()      # Установка дней для тренировок
    setting_meal_time = State()         # Установка времени напоминания о приеме пищи
    setting_meal_count = State()        # Установка количества приемов пищи
    
    # Состояния для рецептов
    waiting_for_recipe_weight = State() # Ожидание ввода веса для расчета порций
    
    # Состояния для калькулятора калорий
    waiting_for_calc_weight = State()   # Ожидание ввода веса для калькулятора
    waiting_for_height = State()        # Ожидание ввода роста
    waiting_for_age = State()           # Ожидание ввода возраста
    waiting_for_gender = State()        # Ожидание выбора пола
    waiting_for_activity = State()      # Ожидание выбора уровня активности
    
    # Состояния для дневника питания
    waiting_for_meal_name = State()     # Ожидание названия приема пищи
    waiting_for_meal_calories = State() # Ожидание ввода калорий
    waiting_for_meal_proteins = State() # Ожидание ввода белков
    waiting_for_meal_fats = State()     # Ожидание ввода жиров
    waiting_for_meal_carbs = State()    # Ожидание ввода углеводов 