import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

bot = Bot(token='')
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    KeyboardButton("/motivation"),
    KeyboardButton("/diet"),
    KeyboardButton("/health_tips"),
    KeyboardButton("/progress"),
    KeyboardButton("/recipes")
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Привет! Я твой фитнес-бот. Вот что я могу:\n"
                        "1. Мотивация — вдохновляющие цитаты.\n"
                        "2. Диета — советы по отслеживанию рациона.\n"
                        "3. Полезные советы для здоровья.\n"
                        "4. Прогресс — как отслеживать достижения.\n"
                        "5. Рецепты — здоровые и вкусные блюда.",
                        reply_markup=keyboard)

@dp.message(Command("motivation"))
async def send_motivation(message: types.Message):
    await message.reply("Не забывай: каждый шаг к цели — это успех!\n"
                        "Подумай о своих целях и запиши их. Это поможет тебе не потерять мотивацию.\n"
                        "Кроме того, вот еще одна цитата: \"Секрет успеха в том, чтобы начать!\"",
                        reply_markup=keyboard)

@dp.message(Command("diet"))
async def send_diet_tracker(message: types.Message):
    await message.reply("Отслеживайте свой рацион, записывая, что вы едите. Можно использовать таблицу или приложение.\n"
                        "Попробуйте вести дневник питания и отмечать свои чувства после еды. Это поможет вам осознать, какие продукты вам подходят.",
                        reply_markup=keyboard)

@dp.message(Command("health_tips"))
async def send_health_tips(message: types.Message):
    await message.reply("Пейте достаточно воды и старайтесь включать в рацион больше овощей!\n"
                        "Также не забывайте про регулярные физические нагрузки. Даже 30 минут в день могут значительно улучшить ваше самочувствие.",
                        reply_markup=keyboard)

@dp.message(Command("progress"))
async def send_progress_statistics(message: types.Message):
    await message.reply("Статистика прогресса поможет вам видеть свои достижения и расширять цели.\n"
                        "Рекомендуется записывать свои замеры каждый месяц и анализировать результаты. Так будет легче понять, что работает, а что нет.",
                        reply_markup=keyboard)

@dp.message(Command("recipes"))
async def send_healthy_recipes(message: types.Message):
    await message.reply("Вот вам простой и здоровый рецепт: Курица с овощами на гриле. Попробуйте!\n"
                        "Инструкция: замаринуйте курицу, добавьте любимые овощи и готовьте на гриле 20-30 минут. "
                        "Подавайте с зеленью и лимоном для усиления вкуса. Приятного аппетита!",
                        reply_markup=keyboard)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

