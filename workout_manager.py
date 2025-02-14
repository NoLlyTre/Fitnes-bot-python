from datetime import datetime, timedelta
from config import WORKOUT_TYPES, CALORIES_PER_MINUTE, EXERCISES

class WorkoutSession:
    def __init__(self):
        self.current_exercise = 0
        self.exercises = []
        self.start_time = None
        self.last_activity = None
        self.completed_exercises = 0
        self.workout_type = None
        
    def start_workout(self, workout_type):
        """Начало тренировки"""
        self.workout_type = workout_type
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.exercises = self._get_exercises_for_type(workout_type)
        if not self.exercises:
            return "Упражнения для данного типа тренировки не найдены"
        return self.exercises[0]

    def next_exercise(self):
        """Переход к следующему упражнению"""
        if self.current_exercise < len(self.exercises) - 1:
            self.current_exercise += 1
            self.completed_exercises += 1
            self.last_activity = datetime.now()
            return self.exercises[self.current_exercise]
        return None

    def previous_exercise(self):
        """Возврат к предыдущему упражнению"""
        if self.current_exercise > 0:
            self.current_exercise -= 1
            self.last_activity = datetime.now()
            return self.exercises[self.current_exercise]
        return None

    def get_current_exercise(self):
        """Получение текущего упражнения"""
        return self.exercises[self.current_exercise]

    def update_activity(self):
        """Обновление времени последней активности"""
        self.last_activity = datetime.now()

    def is_inactive(self, timeout_minutes):
        """Проверка на неактивность"""
        if not self.last_activity:
            return False
        return (datetime.now() - self.last_activity) > timedelta(minutes=timeout_minutes)

    def get_workout_summary(self):
        """Получение сводки по тренировке"""
        duration = (datetime.now() - self.start_time).seconds // 60  # в минутах
        calories = self._calculate_calories(duration)
        
        return {
            'duration': duration,
            'calories_burned': calories,
            'exercises_completed': self.completed_exercises,
            'workout_type': self.workout_type
        }

    def _calculate_calories(self, duration):
        """Расчет сожженных калорий"""
        return CALORIES_PER_MINUTE.get(self.workout_type, 3) * duration

    def _get_exercises_for_type(self, workout_type):
        """Получение списка упражнений для типа тренировки"""
        return EXERCISES.get(workout_type, [])