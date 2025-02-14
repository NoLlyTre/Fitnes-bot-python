from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
import random
import aiosqlite
import logging
from aiogram.exceptions import TelegramBadRequest

from states import UserStates
from keyboards import *
from config import HEALTH_TIPS, RECIPES, WORKOUT_TIPS, NUTRITION_TIPS, MOTIVATION_TIPS
from database import Database
from workout_manager import WorkoutSession
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

# Инициализация базы данных
db = Database()

# Словарь для хранения активных сессий
active_sessions = {}

async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await db.add_user(message.from_user.id, message.from_user.username)
    
    # Получаем имя пользователя, если оно есть, иначе используем "друг"
    user_name = message.from_user.first_name or "друг"
    
    welcome_text = (
        f"✨ Привет, {user_name}! Я твой персональный фитнес-тренер, всегда под рукой!\n\n"
        "🔥 Что я умею:\n"
        "🏋️ Тренировки — программы, упражнения, прогресс\n"
        "📊 Прогресс — вес, калории, статистика\n"
        "🍳 Питание — рецепты, дневник, калькулятор\n"
        "⏰ Напоминания — тренировки, питание\n"
        "💡 Советы — фитнес, здоровье\n\n"
        "Выбирай, с чего начнем! 💪"
    )
    
    try:
        await message.answer_photo(
            photo="https://i.imgur.com/U2KpzSU.jpg",
            caption=welcome_text,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке приветственного фото: {e}")
        # Если не удалось отправить фото, отправляем только текст
        await message.answer(welcome_text, reply_markup=get_main_keyboard())

async def process_menu_selection(callback: types.CallbackQuery):
    """Обработчик выбора раздела меню"""
    menu_type = callback.data.split("_")[1]
    
    try:
        menu_texts = {
            "workouts": "🏋️ Выберите тип тренировки:",
            "progress": "📊 Раздел прогресса:",
            "nutrition": "🍳 Раздел питания:",
            "reminders": "⏰ Настройка напоминаний:",
            "tips": "💡 Полезные советы:"
        }
        
        menu_keyboards = {
            "workouts": get_workouts_keyboard(),
            "progress": get_progress_keyboard(),
            "nutrition": get_nutrition_keyboard(),
            "reminders": get_reminders_keyboard(),
            "tips": get_tips_keyboard()
        }
        
        # Отправляем новое сообщение вместо редактирования
        await callback.message.answer(
            menu_texts.get(menu_type, "Выберите действие:"),
            reply_markup=menu_keyboards.get(menu_type)
        )
        
        # Удаляем предыдущее сообщение после отправки нового
        try:
            await callback.message.delete()
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")
        
    except Exception as e:
        logging.error(f"Ошибка в process_menu_selection: {e}")
        await callback.message.answer(
            "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
    
    try:
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка при ответе на callback: {e}")

async def back_to_main_menu(callback: types.CallbackQuery):
    """Обработчик возврата в главное меню"""
    main_menu_text = "Выберите раздел, который вас интересует:"
    
    try:
        # Удаляем предыдущее сообщение
        await callback.message.delete()
        
        # Отправляем новое сообщение с фото
        await callback.message.answer_photo(
            photo="https://i.imgur.com/U2KpzSU.jpg",
            caption=main_menu_text,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при возврате в главное меню: {e}")
        # Если не удалось отправить фото, отправляем только текст
        await callback.message.edit_text(
            main_menu_text,
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

# Обработчики тренировок
async def process_workout_selection(callback: types.CallbackQuery):
    """Обработчик выбора типа тренировки"""
    # Проверяем, не является ли это напоминанием
    if callback.data == "workout_reminders":
        return
        
    workout_type = callback.data  # Используем полный callback_data
    user_id = callback.from_user.id
    
    session = WorkoutSession()
    first_exercise = session.start_workout(workout_type)
    active_sessions[user_id] = session
    
    if first_exercise == "Упражнения для данного типа тренировки не найдены":
        await callback.message.edit_text(
            "К сожалению, упражнения для данного типа тренировки не найдены. Пожалуйста, выберите другой тип тренировки:",
            reply_markup=get_workouts_keyboard()
        )
    else:
        try:
            # Удаляем предыдущее сообщение
            await callback.message.delete()
            
            # Отправляем новое сообщение с фотографией
            await callback.message.answer_photo(
                photo=first_exercise["photo_url"],
                caption=f"Тренировка началась!\n\n"
                       f"Упражнение 1: {first_exercise['name']}\n"
                       f"👉 {first_exercise['description']}",
                reply_markup=get_exercise_keyboard(session)
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке фото упражнения: {e}")
            # Если не удалось отправить фото, отправляем только текст
            await callback.message.edit_text(
                f"Тренировка началась!\n\n"
                f"Упражнение 1: {first_exercise['name']}\n"
                f"👉 {first_exercise['description']}",
                reply_markup=get_exercise_keyboard(session)
            )

async def process_exercise_navigation(callback: types.CallbackQuery):
    """Обработчик навигации по упражнениям"""
    user_id = callback.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        await callback.answer("Сессия тренировки не найдена")
        return
    
    if callback.data == "next_exercise":
        exercise = session.next_exercise()
    else:
        exercise = session.previous_exercise()
    
    if exercise:
        current_num = session.current_exercise + 1
        try:
            # Удаляем предыдущее сообщение
            await callback.message.delete()
            
            # Отправляем новое сообщение с фотографией
            await callback.message.answer_photo(
                photo=exercise["photo_url"],
                caption=f"Упражнение {current_num}: {exercise['name']}\n"
                       f"👉 {exercise['description']}",
                reply_markup=get_exercise_keyboard(session)
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке фото упражнения: {e}")
            # Если не удалось отправить фото, отправляем только текст
            await callback.message.edit_text(
                f"Упражнение {current_num}: {exercise['name']}\n"
                f"👉 {exercise['description']}",
                reply_markup=get_exercise_keyboard(session)
            )
    await callback.answer()

async def end_workout(callback: types.CallbackQuery):
    """Обработчик завершения тренировки"""
    user_id = callback.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        await callback.answer("Сессия тренировки не найдена")
        return
    
    summary = session.get_workout_summary()
    await db.save_workout(
        user_id,
        summary['workout_type'],
        summary['duration'],
        summary['calories_burned'],
        summary['exercises_completed']
    )
    
    try:
        # Отправляем новое сообщение вместо редактирования
        await callback.message.answer(
            f"Тренировка завершена! 🎉\n\n"
            f"📊 Статистика:\n"
            f"⏱ Длительность: {summary['duration']} минут\n"
            f"🔥 Сожжено калорий: {summary['calories_burned']}\n"
            f"💪 Выполнено упражнений: {summary['exercises_completed']}",
            reply_markup=get_main_keyboard()
        )
        
        # Удаляем предыдущее сообщение
        try:
            await callback.message.delete()
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")
            
    except Exception as e:
        logging.error(f"Ошибка при завершении тренировки: {e}")
        await callback.message.answer(
            "Произошла ошибка при завершении тренировки. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
    
    del active_sessions[user_id]
    await callback.answer()

# Обработчики прогресса
async def process_record_weight(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик записи веса"""
    await callback.message.edit_text(
        "⚖️ Введите ваш текущий вес в килограммах (например: 70.5):"
    )
    await state.set_state(UserStates.waiting_for_weight)
    await callback.answer()

async def save_weight(message: types.Message, state: FSMContext):
    """Сохранение веса пользователя"""
    try:
        weight = float(message.text)
        if weight < 30 or weight > 300:
            await message.answer("Пожалуйста, введите реальный вес (от 30 до 300 кг)")
            return
        
        await db.record_weight(message.from_user.id, weight)
        await state.clear()
        
        await message.answer(
            f"✅ Вес {weight} кг успешно записан!\n\n"
            "Выберите дальнейшее действие:",
            reply_markup=get_progress_keyboard()
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def process_record_measurements(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик записи измерений"""
    await callback.message.edit_text(
        "📏 Давайте запишем ваши измерения!\n"
        "Введите обхват груди в сантиметрах:"
    )
    await state.set_state(UserStates.waiting_for_chest)
    await callback.answer()

async def save_chest(message: types.Message, state: FSMContext):
    """Сохранение обхвата груди"""
    chest = float(message.text)
    await state.update_data(chest=chest)
    await message.answer("Теперь введите обхват талии в сантиметрах:")
    await state.set_state(UserStates.waiting_for_waist)

async def save_waist(message: types.Message, state: FSMContext):
    """Сохранение обхвата талии"""
    waist = float(message.text)
    await state.update_data(waist=waist)
    await message.answer("Введите обхват бёдер в сантиметрах:")
    await state.set_state(UserStates.waiting_for_hips)

async def save_hips(message: types.Message, state: FSMContext):
    """Сохранение обхвата бёдер"""
    hips = float(message.text)
    await state.update_data(hips=hips)
    await message.answer("Введите обхват бицепса в сантиметрах:")
    await state.set_state(UserStates.waiting_for_biceps)

async def save_biceps(message: types.Message, state: FSMContext):
    """Сохранение обхвата бицепса"""
    biceps = float(message.text)
    await state.update_data(biceps=biceps)
    await message.answer("И наконец, введите обхват бедра в сантиметрах:")
    await state.set_state(UserStates.waiting_for_thighs)

async def save_thighs(message: types.Message, state: FSMContext):
    """Сохранение всех измерений"""
    thighs = float(message.text)
    data = await state.get_data()
    await db.record_measurements(
        message.from_user.id,
        data['chest'],
        data['waist'],
        data['hips'],
        data['biceps'],
        thighs
    )
    await state.clear()
    
    await message.answer(
        "✅ Все измерения успешно записаны!\n\n"
        "Выберите дальнейшее действие:",
        reply_markup=get_progress_keyboard()
    )

async def process_show_statistics(callback: types.CallbackQuery):
    """Показ общей статистики"""
    stats = await db.get_user_statistics(callback.from_user.id)
    if stats:
        total_workouts, total_duration, total_calories, total_exercises = stats
        await callback.message.edit_text(
            f"📊 Ваша общая статистика:\n\n"
            f"🏋️‍♂️ Всего тренировок: {total_workouts}\n"
            f"⏱ Общая длительность: {total_duration} минут\n"
            f"🔥 Всего сожжено калорий: {total_calories}\n"
            f"💪 Всего выполнено упражнений: {total_exercises}\n\n"
            "Выберите действие:",
            reply_markup=get_progress_keyboard()
        )
    else:
        await callback.message.edit_text(
            "У вас пока нет завершенных тренировок\n\n"
            "Выберите действие:",
            reply_markup=get_progress_keyboard()
        )
    await callback.answer()

async def process_show_progress(callback: types.CallbackQuery):
    """Показ графика прогресса"""
    # Получаем историю веса
    weight_history = await db.get_weight_history(callback.from_user.id)
    measurements_history = await db.get_measurements_history(callback.from_user.id)
    
    if not weight_history and not measurements_history:
        await callback.message.edit_text(
            "У вас пока нет записей о весе и измерениях.\n"
            "Начните вести учёт, чтобы видеть свой прогресс!\n\n"
            "Выберите действие:",
            reply_markup=get_progress_keyboard()
        )
    else:
        # Формируем текст с историей изменений
        text = "📈 Ваш прогресс:\n\n"
        
        if weight_history:
            text += "⚖️ История изменения веса:\n"
            for weight, date in weight_history[:5]:  # Показываем последние 5 записей
                date_str = datetime.fromisoformat(date).strftime("%d.%m.%Y")
                text += f"{date_str}: {weight} кг\n"
            text += "\n"
        
        if measurements_history:
            text += "📏 Последние измерения:\n"
            chest, waist, hips, biceps, thighs, date = measurements_history[0]
            date_str = datetime.fromisoformat(date).strftime("%d.%m.%Y")
            text += f"Дата: {date_str}\n"
            text += f"Грудь: {chest} см\n"
            text += f"Талия: {waist} см\n"
            text += f"Бёдра: {hips} см\n"
            text += f"Бицепс: {biceps} см\n"
            text += f"Бедро: {thighs} см\n"
        
        await callback.message.edit_text(
            text + "\nВыберите действие:",
            reply_markup=get_progress_keyboard()
        )
    
    await callback.answer()

async def show_health_tip(message: types.Message):
    """Обработчик показа советов по здоровью"""
    tip = random.choice(HEALTH_TIPS)
    await message.answer(f"💡 Совет дня:\n\n{tip}", reply_markup=get_main_keyboard())

# Обработчики напоминаний
async def process_workout_reminder(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик настройки напоминаний о тренировках"""
    await callback.message.edit_text(
        "⏰ Во сколько вы обычно тренируетесь?\n"
        "Укажите время в формате ЧЧ:ММ (например, 18:30):"
    )
    await state.set_state(UserStates.setting_workout_time)
    await callback.answer()

async def save_workout_time(message: types.Message, state: FSMContext):
    """Сохранение времени тренировок"""
    try:
        # Проверка формата времени
        time_str = message.text
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        
        await state.update_data(workout_time=time_str)
        
        # Создаем клавиатуру для выбора дней
        builder = InlineKeyboardBuilder()
        days = {
            "monday": "Понедельник",
            "tuesday": "Вторник",
            "wednesday": "Среда",
            "thursday": "Четверг",
            "friday": "Пятница",
            "saturday": "Суббота",
            "sunday": "Воскресенье"
        }
        
        for day_key, day_name in days.items():
            builder.add(InlineKeyboardButton(
                text=f"☐ {day_name}",
                callback_data=f"day_{day_key}"
            ))
        
        builder.add(InlineKeyboardButton(
            text="✅ Подтвердить выбор",
            callback_data="confirm_days"
        ))
        
        builder.adjust(1)  # Размещаем кнопки в один столбец
        
        await message.answer(
            "Выберите дни недели для тренировок:\n"
            "(Нажмите на день, чтобы выбрать/отменить выбор)",
            reply_markup=builder.as_markup()
        )
        await state.set_state(UserStates.setting_workout_days)
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, укажите время в правильном формате (ЧЧ:ММ)")

async def process_day_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора дней недели"""
    try:
        # Проверяем, что это callback для выбора дня недели, а не статистики
        if not callback.data.startswith("day_") or callback.data == "day_stats":
            return
            
        day = callback.data.split('_')[1]
        current_text = callback.message.reply_markup.inline_keyboard
        
        days_mapping = {
            "monday": ("Понедельник", 1),
            "tuesday": ("Вторник", 2),
            "wednesday": ("Среда", 3),
            "thursday": ("Четверг", 4),
            "friday": ("Пятница", 5),
            "saturday": ("Суббота", 6),
            "sunday": ("Воскресенье", 7)
        }
        
        if day not in days_mapping:
            logging.error(f"Неверный день недели в callback_data: {day}")
            await callback.answer("Произошла ошибка. Попробуйте еще раз.")
            return
        
        builder = InlineKeyboardBuilder()
        
        # Обновляем состояние кнопок
        for row in current_text[:-1]:  # Исключаем кнопку подтверждения
            button = row[0]
            day_key = button.callback_data.split('_')[1]
            
            if day_key not in days_mapping:
                continue
                
            day_name = days_mapping[day_key][0]
            
            if day_key == day:
                # Меняем состояние нажатой кнопки
                is_selected = "☑" in button.text
                new_text = f"☐ {day_name}" if is_selected else f"☑ {day_name}"
            else:
                new_text = button.text
            
            builder.add(InlineKeyboardButton(
                text=new_text,
                callback_data=f"day_{day_key}"
            ))
        
        # Добавляем кнопку подтверждения
        builder.add(InlineKeyboardButton(
            text="✅ Подтвердить выбор",
            callback_data="confirm_days"
        ))
        
        builder.adjust(1)
        
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
        
    except Exception as e:
        logging.error(f"Ошибка в process_day_selection: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")
    
    await callback.answer()

async def confirm_days_selection(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение выбора дней"""
    selected_days = []
    days_mapping = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 7
    }
    
    # Собираем выбранные дни
    for row in callback.message.reply_markup.inline_keyboard[:-1]:  # Исключаем кнопку подтверждения
        button = row[0]
        if "☑" in button.text:
            day_key = button.callback_data.split('_')[1]
            selected_days.append(str(days_mapping[day_key]))
    
    if not selected_days:
        await callback.answer("Выберите хотя бы один день!", show_alert=True)
        return
    
    data = await state.get_data()
    workout_time = data.get('workout_time')
    days_str = ','.join(selected_days)
    
    # Сохраняем в базу данных
    await db.save_workout_reminder(callback.from_user.id, workout_time, days_str)
    
    # Преобразуем номера дней в названия для отображения
    day_names = {
        "1": "Пн",
        "2": "Вт",
        "3": "Ср",
        "4": "Чт",
        "5": "Пт",
        "6": "Сб",
        "7": "Вс"
    }
    selected_day_names = [day_names[day] for day in selected_days]
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Напоминания о тренировках настроены!\n"
        f"Время: {workout_time}\n"
        f"Дни: {', '.join(selected_day_names)}\n\n"
        "Выберите действие:",
        reply_markup=get_reminders_keyboard()
    )
    await callback.answer()

async def process_meal_reminder(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик настройки напоминаний о питании"""
    await callback.message.edit_text(
        "🍽 Сколько раз в день вы принимаете пищу? (от 3 до 6):"
    )
    await state.set_state(UserStates.setting_meal_count)
    await callback.answer()

async def save_meal_count(message: types.Message, state: FSMContext):
    """Сохранение количества приемов пищи"""
    try:
        meal_count = int(message.text)
        if not (3 <= meal_count <= 6):
            raise ValueError
        
        await state.update_data(meal_count=meal_count, current_meal=1, meal_times=[])
        await message.answer(
            f"Укажите время {1}-го приема пищи в формате ЧЧ:ММ\n"
            "Например: 08:00"
        )
        await state.set_state(UserStates.setting_meal_time)
    except ValueError:
        await message.answer("Пожалуйста, укажите число от 3 до 6")

async def save_meal_time(message: types.Message, state: FSMContext):
    """Сохранение времени приемов пищи"""
    try:
        time_str = message.text
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        
        data = await state.get_data()
        meal_count = data.get('meal_count')
        current_meal = data.get('current_meal')
        meal_times = data.get('meal_times', [])
        
        # Проверяем, чтобы время было позже предыдущего
        if meal_times:
            last_time = meal_times[-1]
            last_hour, last_minute = map(int, last_time.split(':'))
            current_hour, current_minute = map(int, time_str.split(':'))
            if (current_hour < last_hour) or (current_hour == last_hour and current_minute <= last_minute):
                await message.answer(
                    f"Время {time_str} должно быть позже предыдущего приема пищи ({last_time}).\n"
                    f"Пожалуйста, введите корректное время для {current_meal}-го приема пищи:"
                )
                return
        
        # Добавляем текущее время в список
        meal_times.append(time_str)
        await state.update_data(meal_times=meal_times, current_meal=current_meal + 1)
        
        # Если это не последний прием пищи, запрашиваем следующий
        if current_meal < meal_count:
            await message.answer(
                f"Укажите время {current_meal + 1}-го приема пищи в формате ЧЧ:ММ\n"
                "Например: 12:00"
            )
        else:
            # Сохраняем все времена приемов пищи в базу данных
            times_str = ','.join(meal_times)
            await db.save_meal_reminder(message.from_user.id, meal_count, times_str)
            
            # Форматируем времена для отображения
            times_display = '\n'.join([f"🕐 {i+1}-й прием пищи: {time}" 
                                     for i, time in enumerate(meal_times)])
            
            await state.clear()
            await message.answer(
                f"✅ Напоминания о питании настроены!\n\n"
                f"Количество приемов пищи: {meal_count}\n"
                f"Расписание:\n{times_display}\n\n"
                "Выберите действие:",
                reply_markup=get_reminders_keyboard()
            )
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, укажите время в правильном формате (ЧЧ:ММ)")

async def process_reminder_settings(callback: types.CallbackQuery):
    """Обработчик настроек напоминаний"""
    # Получаем текущие настройки из базы данных
    workout_reminder = await db.get_workout_reminders(callback.from_user.id)
    meal_reminder = await db.get_meal_reminders(callback.from_user.id)
    
    workout_status = "Не настроены"
    if workout_reminder:
        time, days = workout_reminder
        days_list = days.split(',')
        workout_status = f"Время: {time}, Дни: {', '.join(days_list)}"
    
    meal_status = "Не настроено"
    if meal_reminder:
        count, times_str = meal_reminder
        times_list = times_str.split(',')
        meal_times = '\n'.join([f"🕐 {i+1}-й прием пищи: {time}" 
                               for i, time in enumerate(times_list)])
        meal_status = f"{count} раз(а) в день\n{meal_times}"
    
    await callback.message.edit_text(
        "⚙️ Текущие настройки напоминаний:\n\n"
        f"🏋️ Тренировки: {workout_status}\n\n"
        f"🍽 Питание: {meal_status}\n\n"
        "Выберите тип напоминаний для настройки:",
        reply_markup=get_reminders_keyboard()
    )
    await callback.answer()

# Обработчики раздела питания
async def process_nutrition_recipes(callback: types.CallbackQuery):
    """Обработчик раздела рецептов"""
    try:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🥗 Рецепты для похудения", callback_data="recipes_loss"))
        builder.add(InlineKeyboardButton(text="🍖 Рецепты для набора массы", callback_data="recipes_gain"))
        builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="menu_nutrition"))
        builder.adjust(1)
        
        message_text = "Выберите категорию рецептов:"
        
        try:
            # Пробуем отредактировать существующее сообщение
            await callback.message.edit_text(
                text=message_text,
                reply_markup=builder.as_markup()
            )
        except (AttributeError, TelegramBadRequest):
            # Если не получается отредактировать, отправляем новое сообщение
            try:
                # Пытаемся удалить предыдущее сообщение
                await callback.message.delete()
            except Exception as e:
                logging.error(f"Ошибка при удалении сообщения: {e}")
            
            # Отправляем новое сообщение
            await callback.message.answer(
                text=message_text,
                reply_markup=builder.as_markup()
            )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Ошибка в process_nutrition_recipes: {e}")
        try:
            await callback.message.answer(
                "Произошла ошибка при загрузке рецептов. Пожалуйста, попробуйте позже.",
                reply_markup=InlineKeyboardBuilder()
                .add(InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_to_main"))
                .as_markup()
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения об ошибке: {e}")
        
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

async def process_recipes_category(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора категории рецептов"""
    try:
        category = callback.data.split('_')[1]  # loss или gain
        
        recipes = RECIPES.get(category, [])
        if not recipes:
            await callback.answer("Рецепты не найдены")
            return
        
        builder = InlineKeyboardBuilder()
        
        # Добавляем кнопку для каждого рецепта
        for recipe in recipes:
            builder.add(InlineKeyboardButton(
                text=recipe['name'],
                callback_data=f"recipe_{category}_{recipes.index(recipe)}"
            ))
        
        builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="nutrition_recipes"))
        builder.adjust(1)  # Размещаем кнопки в один столбец
        
        try:
            # Пробуем отредактировать существующее сообщение
            await callback.message.edit_text(
                "Выберите рецепт:",
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            # Если не получается отредактировать, отправляем новое сообщение
            try:
                await callback.message.delete()
            except:
                pass
            await callback.message.answer(
                "Выберите рецепт:",
                reply_markup=builder.as_markup()
            )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Ошибка в process_recipes_category: {e}")
        try:
            await callback.message.answer(
                "Произошла ошибка при загрузке рецептов. Пожалуйста, попробуйте позже.",
                reply_markup=InlineKeyboardBuilder()
                .add(InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_to_main"))
                .as_markup()
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения об ошибке: {e}")
        
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

async def process_recipe_details(callback: types.CallbackQuery):
    """Обработчик показа деталей рецепта"""
    try:
        _, category, recipe_index = callback.data.split('_')
        recipe_index = int(recipe_index)
        
        recipes = RECIPES.get(category, [])
        if not recipes or recipe_index >= len(recipes):
            await callback.answer("Рецепт не найден")
            return
        
        recipe = recipes[recipe_index]
        
        # Получаем последний записанный вес пользователя из базы данных
        async with aiosqlite.connect('fitness_bot.db') as db:
            async with db.execute(
                """
                SELECT weight 
                FROM weight_records 
                WHERE user_id = ? 
                ORDER BY recorded_at DESC 
                LIMIT 1
                """,
                (callback.from_user.id,)
            ) as cursor:
                weight_record = await cursor.fetchone()
        
        if not weight_record:
            # Если вес не найден, предлагаем записать его через раздел прогресса
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(text="📊 Записать вес", callback_data="record_weight"))
            builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data=f"recipes_{category}"))
            builder.adjust(1)
            
            await callback.message.edit_text(
                "Для расчета индивидуальных порций необходимо знать ваш вес.\n"
                "Пожалуйста, запишите свой вес в разделе прогресса:",
                reply_markup=builder.as_markup()
            )
            return
        
        user_weight = weight_record[0]
        
        # Формируем текст с деталями рецепта
        text = f"🍽 {recipe['name']} - {recipe['calories']} ккал\n\n"
        text += "Ингредиенты (для вашего веса):\n"
        
        # Рассчитываем множитель для корректировки порций
        weight_multiplier = user_weight / recipe['base_weight']
        
        for ingredient, details in recipe['ingredients'].items():
            amount = details['amount']
            unit = details['unit']
            
            # Корректируем количество в зависимости от веса пользователя
            if unit != 'шт':  # Не умножаем количество для штучных ингредиентов
                amount = round(amount * weight_multiplier, 1)
            
            text += f"- {ingredient}: {amount} {unit}\n"
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="↩️ К списку рецептов", callback_data=f"recipes_{category}"))
        builder.add(InlineKeyboardButton(text="↩️ К категориям", callback_data="nutrition_recipes"))
        builder.adjust(1)
        
        try:
            # Удаляем предыдущее сообщение
            await callback.message.delete()
            
            # Отправляем новое сообщение с фотографией
            await callback.message.answer_photo(
                photo=recipe['photo_url'],
                caption=f"Рецепт для веса {user_weight} кг:\n\n{text}",
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            # В случае ошибки с фото, отправляем только текст
            await callback.message.answer(
                f"Рецепт для веса {user_weight} кг:\n\n{text}",
                reply_markup=builder.as_markup()
            )
            
        await callback.answer()
        
    except Exception as e:
        # Общая обработка ошибок
        logging.error(f"Ошибка при показе рецепта: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке рецепта. Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="↩️ Назад", callback_data="nutrition_recipes")
            ).as_markup()
        )

async def process_nutrition_calculator(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик калькулятора калорий"""
    await state.set_state(UserStates.waiting_for_calc_weight)
    
    try:
        await callback.message.answer(
            "🔢 Калькулятор калорий\n\n"
            "Давайте рассчитаем вашу суточную норму калорий.\n"
            "Для начала введите ваш вес в килограммах (например: 70.5):"
        )
        
        # Удаляем предыдущее сообщение
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Ошибка в process_nutrition_calculator: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

async def save_calc_weight(message: types.Message, state: FSMContext):
    """Сохранение веса для калькулятора калорий"""
    try:
        weight = float(message.text)
        if weight < 30 or weight > 300:
            await message.answer("Пожалуйста, введите реальный вес (от 30 до 300 кг)")
            return
        
        await state.update_data(weight=weight)
        await state.set_state(UserStates.waiting_for_height)
        await message.answer("Теперь введите ваш рост в сантиметрах (например: 175):")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def save_height(message: types.Message, state: FSMContext):
    """Сохранение роста"""
    try:
        height = float(message.text)
        if height < 100 or height > 250:
            await message.answer("Пожалуйста, введите реальный рост (от 100 до 250 см)")
            return
        
        await state.update_data(height=height)
        await state.set_state(UserStates.waiting_for_age)
        await message.answer("Введите ваш возраст:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def save_age(message: types.Message, state: FSMContext):
    """Сохранение возраста"""
    try:
        age = int(message.text)
        if age < 14 or age > 100:
            await message.answer("Пожалуйста, введите реальный возраст (от 14 до 100 лет)")
            return
        
        await state.update_data(age=age)
        
        # Создаем клавиатуру для выбора пола
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Мужской", callback_data="gender_male"))
        builder.add(InlineKeyboardButton(text="Женский", callback_data="gender_female"))
        builder.adjust(2)
        
        await state.set_state(UserStates.waiting_for_gender)
        await message.answer("Выберите ваш пол:", reply_markup=builder.as_markup())
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def save_gender(callback: types.CallbackQuery, state: FSMContext):
    """Сохранение пола"""
    gender = callback.data.split('_')[1]
    await state.update_data(gender=gender)
    
    # Создаем клавиатуру для выбора уровня активности
    builder = InlineKeyboardBuilder()
    activities = {
        "minimal": "Минимальная активность (сидячая работа)",
        "low": "Низкая активность (легкие тренировки 1-3 раза в неделю)",
        "medium": "Средняя активность (умеренные тренировки 3-5 раз в неделю)",
        "high": "Высокая активность (интенсивные тренировки 6-7 раз в неделю)",
        "very_high": "Очень высокая активность (спортсмены)"
    }
    
    for key, value in activities.items():
        builder.add(InlineKeyboardButton(text=value, callback_data=f"activity_{key}"))
    
    builder.adjust(1)
    
    await state.set_state(UserStates.waiting_for_activity)
    await callback.message.edit_text(
        "Выберите ваш уровень физической активности:",
        reply_markup=builder.as_markup()
    )

async def calculate_calories(callback: types.CallbackQuery, state: FSMContext):
    """Расчет калорий"""
    activity = callback.data.split('_')[1]
    data = await state.get_data()
    
    # Коэффициенты активности
    activity_factors = {
        "minimal": 1.2,
        "low": 1.375,
        "medium": 1.55,
        "high": 1.725,
        "very_high": 1.9
    }
    
    # Расчет базового обмена веществ (формула Миффлина-Сан Жеора)
    if data['gender'] == 'male':
        bmr = 10 * data['weight'] + 6.25 * data['height'] - 5 * data['age'] + 5
    else:
        bmr = 10 * data['weight'] + 6.25 * data['height'] - 5 * data['age'] - 161
    
    # Расчет суточной нормы калорий
    daily_calories = round(bmr * activity_factors[activity])
    
    # Расчет норм для разных целей
    weight_loss = round(daily_calories * 0.85)  # Дефицит 15%
    weight_gain = round(daily_calories * 1.15)  # Профицит 15%
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="menu_nutrition"))
    
    await callback.message.edit_text(
        f"📊 Результаты расчета калорий:\n\n"
        f"Ваша суточная норма калорий: {daily_calories} ккал\n\n"
        f"Для разных целей:\n"
        f"🔽 Снижение веса: {weight_loss} ккал\n"
        f"➡️ Поддержание веса: {daily_calories} ккал\n"
        f"🔼 Набор массы: {weight_gain} ккал\n\n"
        f"💡 Совет: Для здорового изменения веса рекомендуется\n"
        f"придерживаться дефицита/профицита не более 15%",
        reply_markup=builder.as_markup()
    )
    
    await state.clear()

async def process_nutrition_diary(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик дневника питания"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📝 Записать прием пищи", callback_data="add_meal"))
    builder.add(InlineKeyboardButton(text="📊 Статистика за день", callback_data="day_stats"))
    builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="menu_nutrition"))
    builder.adjust(1)
    
    try:
        await callback.message.answer(
            "📝 Дневник питания\n\n"
            "Выберите действие:",
            reply_markup=builder.as_markup()
        )
        
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Ошибка в process_nutrition_diary: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

async def start_add_meal(callback: types.CallbackQuery, state: FSMContext):
    """Начало записи приема пищи"""
    await state.set_state(UserStates.waiting_for_meal_name)
    await callback.message.edit_text(
        "Введите название продукта или блюда:"
    )

async def save_meal_name(message: types.Message, state: FSMContext):
    """Сохранение названия продукта"""
    await state.update_data(meal_name=message.text)
    await state.set_state(UserStates.waiting_for_meal_calories)
    await message.answer("Введите количество калорий:")

async def save_meal_calories(message: types.Message, state: FSMContext):
    """Сохранение калорий"""
    try:
        calories = float(message.text)
        if calories < 0 or calories > 5000:
            await message.answer("Пожалуйста, введите реальное количество калорий (от 0 до 5000)")
            return
        
        await state.update_data(calories=calories)
        await state.set_state(UserStates.waiting_for_meal_proteins)
        await message.answer("Введите количество белков в граммах:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def save_meal_proteins(message: types.Message, state: FSMContext):
    """Сохранение белков"""
    try:
        proteins = float(message.text)
        if proteins < 0 or proteins > 300:
            await message.answer("Пожалуйста, введите реальное количество белков (от 0 до 300)")
            return
        
        await state.update_data(proteins=proteins)
        await state.set_state(UserStates.waiting_for_meal_fats)
        await message.answer("Введите количество жиров в граммах:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def save_meal_fats(message: types.Message, state: FSMContext):
    """Сохранение жиров"""
    try:
        fats = float(message.text)
        if fats < 0 or fats > 300:
            await message.answer("Пожалуйста, введите реальное количество жиров (от 0 до 300)")
            return
        
        await state.update_data(fats=fats)
        await state.set_state(UserStates.waiting_for_meal_carbs)
        await message.answer("Введите количество углеводов в граммах:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def save_meal_carbs(message: types.Message, state: FSMContext):
    """Сохранение углеводов и всей записи"""
    try:
        carbs = float(message.text)
        if carbs < 0 or carbs > 300:
            await message.answer("Пожалуйста, введите реальное количество углеводов (от 0 до 300)")
            return
        
        data = await state.get_data()
        current_time = datetime.now().strftime("%H:%M")
        
        # Сохраняем в базу данных
        async with aiosqlite.connect('fitness_bot.db') as db:
            await db.execute("""
                INSERT INTO meal_diary (
                    user_id, meal_name, calories, proteins, fats, carbs, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (
                message.from_user.id, data['meal_name'], data['calories'],
                data['proteins'], data['fats'], carbs
            ))
            await db.commit()
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="📝 Записать еще", callback_data="add_meal"))
        builder.add(InlineKeyboardButton(text="📊 Статистика за день", callback_data="day_stats"))
        builder.add(InlineKeyboardButton(text="↩️ В меню питания", callback_data="menu_nutrition"))
        builder.adjust(1)
        
        await message.answer(
            f"✅ Запись добавлена в дневник питания!\n\n"
            f"🕐 Время: {current_time}\n"
            f"🍽 Продукт: {data['meal_name']}\n"
            f"📊 Нутриенты:\n"
            f"• Калории: {data['calories']} ккал\n"
            f"• Белки: {data['proteins']} г\n"
            f"• Жиры: {data['fats']} г\n"
            f"• Углеводы: {carbs} г",
            reply_markup=builder.as_markup()
        )
        
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение")

async def show_day_stats(callback: types.CallbackQuery):
    """Показ статистики за день"""
    logging.info(f"Начало выполнения show_day_stats для пользователя {callback.from_user.id}")
    try:
        async with aiosqlite.connect('fitness_bot.db') as db:
            logging.info("Подключение к БД установлено")
            
            # Получаем последнюю запись о весе пользователя
            logging.info("Запрос веса пользователя из БД")
            async with db.execute("""
                SELECT weight FROM weight_records 
                WHERE user_id = ? 
                ORDER BY recorded_at DESC LIMIT 1
            """, (callback.from_user.id,)) as cursor:
                weight_record = await cursor.fetchone()
                logging.info(f"Получена запись о весе: {weight_record}")

            # Получаем сумму всех нутриентов за сегодня
            logging.info("Запрос статистики питания за день")
            async with db.execute("""
                SELECT 
                    SUM(calories) as total_calories,
                    SUM(proteins) as total_proteins,
                    SUM(fats) as total_fats,
                    SUM(carbs) as total_carbs,
                    COUNT(*) as meals_count
                FROM meal_diary
                WHERE user_id = ? 
                AND date(recorded_at) = date('now', 'localtime')
            """, (callback.from_user.id,)) as cursor:
                stats = await cursor.fetchone()
                logging.info(f"Получена статистика: {stats}")
            
            # Получаем все приемы пищи за сегодня
            logging.info("Запрос списка приемов пищи")
            async with db.execute("""
                SELECT meal_name, calories, proteins, fats, carbs, time(recorded_at)
                FROM meal_diary
                WHERE user_id = ? 
                AND date(recorded_at) = date('now', 'localtime')
                ORDER BY recorded_at
            """, (callback.from_user.id,)) as cursor:
                meals = await cursor.fetchall()
                logging.info(f"Получено приемов пищи: {len(meals)}")
        
        if not stats[0]:  # Если нет записей за сегодня
            logging.info("Нет записей за сегодня")
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(text="📝 Записать прием пищи", callback_data="add_meal"))
            builder.add(InlineKeyboardButton(text="↩️ Назад", callback_data="menu_nutrition"))
            builder.adjust(1)
            
            await callback.message.edit_text(
                "За сегодня еще нет записей в дневнике питания.",
                reply_markup=builder.as_markup()
            )
            return
        
        total_calories, total_proteins, total_fats, total_carbs, meals_count = stats
        logging.info(f"Обработка статистики: калории={total_calories}, белки={total_proteins}, жиры={total_fats}, углеводы={total_carbs}, приемов пищи={meals_count}")
        
        # Расчет рекомендуемых норм на основе веса (если есть)
        if weight_record:
            logging.info("Расчет норм на основе веса")
            weight = weight_record[0]
            recommended_calories = weight * 30
            recommended_proteins = weight * 2
            recommended_fats = weight * 1
            recommended_carbs = weight * 3
            
            calories_percent = round((total_calories / recommended_calories) * 100, 1)
            proteins_percent = round((total_proteins / recommended_proteins) * 100, 1)
            fats_percent = round((total_fats / recommended_fats) * 100, 1)
            carbs_percent = round((total_carbs / recommended_carbs) * 100, 1)
            
            logging.info(f"Проценты от нормы: калории={calories_percent}%, белки={proteins_percent}%, жиры={fats_percent}%, углеводы={carbs_percent}%")
            
            # Формируем текст со статистикой
            text = f"📊 Статистика питания за сегодня:\n\n"
            text += f"Всего приемов пищи: {meals_count}\n\n"
            text += f"Общие показатели (% от нормы):\n"
            text += f"• Калории: {total_calories:.1f} ккал ({calories_percent}%)\n"
            text += f"• Белки: {total_proteins:.1f} г ({proteins_percent}%)\n"
            text += f"• Жиры: {total_fats:.1f} г ({fats_percent}%)\n"
            text += f"• Углеводы: {total_carbs:.1f} г ({carbs_percent}%)\n\n"
            
            # Добавляем рекомендации
            if calories_percent < 70:
                text += "⚠️ Калорий меньше нормы. Рекомендуется увеличить прием пищи.\n"
            elif calories_percent > 130:
                text += "⚠️ Превышение калорий. Рекомендуется уменьшить порции.\n"
            
            if proteins_percent < 70:
                text += "💪 Недостаточно белка. Добавьте мясо, рыбу или молочные продукты.\n"
        else:
            logging.info("Формирование статистики без веса пользователя")
            text = f"📊 Статистика питания за сегодня:\n\n"
            text += f"Всего приемов пищи: {meals_count}\n\n"
            text += f"Общие показатели:\n"
            text += f"• Калории: {total_calories:.1f} ккал\n"
            text += f"• Белки: {total_proteins:.1f} г\n"
            text += f"• Жиры: {total_fats:.1f} г\n"
            text += f"• Углеводы: {total_carbs:.1f} г\n\n"
            text += "ℹ️ Запишите свой вес в разделе прогресса для расчета персональных норм.\n\n"
        
        text += "\nПриемы пищи:\n"
        for meal in meals:
            name, cals, prots, fats, carbs, time = meal
            time = time.split('.')[0]  # Убираем миллисекунды
            text += f"\n🕐 {time}\n"
            text += f"🍽 {name}\n"
            text += f"📊 {cals} ккал (Б: {prots}г, Ж: {fats}г, У: {carbs}г)\n"
        
        logging.info("Формирование клавиатуры")
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="📝 Записать прием пищи", callback_data="add_meal"))
        builder.add(InlineKeyboardButton(text="↩️ В меню питания", callback_data="menu_nutrition"))
        builder.adjust(1)
        
        try:
            logging.info("Попытка редактирования сообщения")
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            logging.info("Сообщение успешно отредактировано")
        except TelegramBadRequest as e:
            logging.error(f"Ошибка при редактировании сообщения: {e}")
            logging.info("Попытка отправки нового сообщения")
            await callback.message.answer(text, reply_markup=builder.as_markup())
            try:
                logging.info("Попытка удаления старого сообщения")
                await callback.message.delete()
                logging.info("Старое сообщение успешно удалено")
            except Exception as e:
                logging.error(f"Ошибка при удалении старого сообщения: {e}")
        
    except Exception as e:
        logging.error(f"Критическая ошибка в show_day_stats: {str(e)}")
        logging.exception(e)  # Это выведет полный стек ошибки
        await callback.message.edit_text(
            "Произошла ошибка при загрузке статистики. Попробуйте позже.",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="↩️ Назад", callback_data="menu_nutrition")
            ).as_markup()
        )
    
    logging.info("Завершение выполнения show_day_stats")
    await callback.answer()

async def process_tips_section(callback: types.CallbackQuery):
    """Обработчик раздела советов"""
    try:
        tips_type = callback.data.split('_')[1]
        
        tips_mapping = {
            'workout': WORKOUT_TIPS,
            'nutrition': NUTRITION_TIPS,
            'motivation': MOTIVATION_TIPS
        }
        
        titles_mapping = {
            'workout': '🏋️ Советы по тренировкам',
            'nutrition': '🥗 Советы по питанию',
            'motivation': '💪 Мотивация'
        }
        
        tips = tips_mapping.get(tips_type, [])
        title = titles_mapping.get(tips_type, 'Советы')
        
        if not tips:
            await callback.answer("Советы не найдены")
            return
            
        tip = random.choice(tips)
        
        try:
            # Отправляем новое сообщение
            await callback.message.answer(
                f"{title}\n\n{tip}",
                reply_markup=get_tips_keyboard()
            )
            
            # Удаляем предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception as e:
                logging.error(f"Ошибка при удалении сообщения: {e}")
                
        except Exception as e:
            logging.error(f"Ошибка при отправке совета: {e}")
            await callback.message.answer(
                "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
                reply_markup=get_tips_keyboard()
            )
    
    except Exception as e:
        logging.error(f"Ошибка в process_tips_section: {e}")
        try:
            await callback.message.answer(
                "Произошла ошибка. Пожалуйста, попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения об ошибке: {e}")
            pass
    
    await callback.answer()

async def register_handlers(dp):
    """Регистрация всех обработчиков"""
    # Базовые команды
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(show_health_tip, Command(commands=["tip"]))

    # Обработчики меню и навигации
    dp.callback_query.register(back_to_main_menu, F.data == "back_to_main")
    dp.callback_query.register(process_menu_selection, F.data.startswith("menu_"))

    # Обработчики тренировок
    dp.callback_query.register(process_workout_selection, F.data.startswith("workout_"))
    dp.callback_query.register(process_exercise_navigation, F.data.in_(["next_exercise", "prev_exercise"]))
    dp.callback_query.register(end_workout, F.data == "end_workout")

    # Обработчики прогресса
    dp.callback_query.register(process_record_weight, F.data == "record_weight")
    dp.callback_query.register(process_record_measurements, F.data == "record_measurements")
    dp.callback_query.register(process_show_statistics, F.data == "show_statistics")
    dp.callback_query.register(process_show_progress, F.data == "show_progress")

    # Обработчики питания
    dp.callback_query.register(process_nutrition_recipes, F.data == "nutrition_recipes")
    dp.callback_query.register(process_recipes_category, F.data.startswith("recipes_"))
    dp.callback_query.register(process_recipe_details, F.data.startswith("recipe_"))
    dp.callback_query.register(process_nutrition_calculator, F.data == "nutrition_calculator")
    dp.callback_query.register(process_nutrition_diary, F.data == "nutrition_diary")

    # Обработчики напоминаний
    dp.callback_query.register(process_workout_reminder, F.data == "workout_reminders")
    dp.callback_query.register(process_meal_reminder, F.data == "meal_reminders")
    dp.callback_query.register(process_reminder_settings, F.data == "reminder_settings")
    dp.callback_query.register(process_day_selection, F.data.startswith("day_"))
    dp.callback_query.register(confirm_days_selection, F.data == "confirm_days")

    # Обработчики советов
    dp.callback_query.register(process_tips_section, F.data.startswith("tips_"))

    # Обработчики состояний
    dp.message.register(save_weight, UserStates.waiting_for_weight)
    dp.message.register(save_chest, UserStates.waiting_for_chest)
    dp.message.register(save_waist, UserStates.waiting_for_waist)
    dp.message.register(save_hips, UserStates.waiting_for_hips)
    dp.message.register(save_biceps, UserStates.waiting_for_biceps)
    dp.message.register(save_thighs, UserStates.waiting_for_thighs)
    dp.message.register(save_workout_time, UserStates.setting_workout_time)
    dp.message.register(save_meal_count, UserStates.setting_meal_count)
    dp.message.register(save_meal_time, UserStates.setting_meal_time)

    # Обработчики калькулятора калорий
    dp.callback_query.register(process_nutrition_calculator, F.data == "nutrition_calculator")
    dp.message.register(save_calc_weight, UserStates.waiting_for_calc_weight)
    dp.message.register(save_height, UserStates.waiting_for_height)
    dp.message.register(save_age, UserStates.waiting_for_age)
    dp.callback_query.register(save_gender, F.data.startswith("gender_"))
    dp.callback_query.register(calculate_calories, F.data.startswith("activity_"))

    # Обработчики дневника питания
    dp.callback_query.register(process_nutrition_diary, F.data == "nutrition_diary")
    dp.callback_query.register(start_add_meal, F.data == "add_meal")
    dp.callback_query.register(show_day_stats, F.data == "day_stats")
    dp.message.register(save_meal_name, UserStates.waiting_for_meal_name)
    dp.message.register(save_meal_calories, UserStates.waiting_for_meal_calories)
    dp.message.register(save_meal_proteins, UserStates.waiting_for_meal_proteins)
    dp.message.register(save_meal_fats, UserStates.waiting_for_meal_fats)
    dp.message.register(save_meal_carbs, UserStates.waiting_for_meal_carbs) 