import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F

bot = Bot(token='7997378459:AAE4Sd0D-Sjbf-bvEfub7cHeVSIStKLMjuc')
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Привет! Я твой фитнес-бот. Вот что я могу:\n"
                        "/motivation - Мотивационные советы\n"
                        "/diet - Трекер питания\n"
                        "/health_tips - Советы по здоровью\n"
                        "/progress - Статистика прогресса\n"
                        "/recipes - Предложения о здоровых рецептах")

@dp.message(Command("motivation"))
async def send_motivation(message: types.Message):
    await message.reply("Не забывай: каждый шаг к цели — это успех!")

@dp.message(Command("diet"))
async def send_diet_tracker(message: types.Message):
    await message.reply("Отслеживайте свой рацион, записывая, что вы едите. Можно использовать таблицу или приложение.")

@dp.message(Command("health_tips"))
async def send_health_tips(message: types.Message):
    await message.reply("Пейте достаточно воды и старайтесь включать в рацион больше овощей!")

@dp.message(Command("progress"))
async def send_progress_statistics(message: types.Message):
    await message.reply("Статистика прогресса поможет вам видеть свои достижения и расширять цели.")

@dp.message(Command("recipes"))
async def send_healthy_recipes(message: types.Message):
    await message.reply("Вот вам простой и здоровый рецепт: Курица с овощами на гриле. Попробуйте!")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())