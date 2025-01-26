**Немного о боте:**

BodyIsFine это Telegram-бот, предназначенный для предоставления пользователям советов и рекомендаций по фитнесу. Бот предлагает информацию о рекомендациях по выполнению упражнений, планах диеты и общем самочувствии, чтобы помочь людям достичь своих целей в фитнесе.

**Функции:**

Сохраняйте мотивацию с помощью регулярных советов и напоминаний по фитнесу

Получите отслеживание рациона

Получите советы по здоровью

Получите статистику прогресса

Получите предложения о здоровых рецептах

**Библиотека aiogram**
- import logging: Отображает логи (ошибки, события)
- from aiogram import Bot, Dispatcher, types:
  - Bot: Класс для взаимодействия с Telegram API.
  - Dispatcher: Класс для обработки обновлений и маршрутизации команд.
  - types: Модуль, который включает различные данные и типы, используемые в Telegram, такие как сообщения, кнопки и т.д.
- from aiogram.filters import Command: Фильтрация команд, позволяющая проверять является ли сообщение командой (нужно будет добавить комманды в BotFather)
- from aiogram.types import ReplyKeyboardMarkup, KeyboardButton: Создание внутренней клавиатуры


**Начало работы:**

Чтобы начать пользоваться ботом BodyIsFine, выполните следующие действия:

Создайте аккаунт в Telegram, если у вас его еще нет.

Найдите «@BodyIsFine_bot» в приложении Telegram.

Начните разговор с ботом. Для этого отправьте сообщение боту (/start), чтобы получить выбор функций.

**Функции у бота:**

/motivation - Мотивационные советы

/diet - Трекер питания

/health_tips - Советы по здоровью

/progress - Статистика прогресса

/recipes - Предложения о здоровых рецептах

**Контакт**

По любым вопросам или поддержке относительно бота BodyIsFine, пожалуйста, свяжитесь с нами по адресу позже
