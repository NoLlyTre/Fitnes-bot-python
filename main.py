import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command 

logging.basicConfig(level=logging.INFO)


TOKEN = ""

bot = Bot(token=TOKEN)
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мотивация")],
        [KeyboardButton(text="Диета")],
        [KeyboardButton(text="Советы по здоровью")],
        [KeyboardButton(text="Прогресс")],
        [KeyboardButton(text="Рецепты")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я твой фитнес-бот. Вот что я могу:\n"
        "1. 'Мотивация' — вдохновляющие цитаты.\n"
        "2. 'Диета' — советы по отслеживанию рациона.\n"
        "3. 'Советы по здоровью' — полезные рекомендации.\n"
        "4. 'Прогресс' — как отслеживать достижения.\n"
        "5. 'Рецепты' — здоровые и вкусные блюда.",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "Мотивация")
async def send_motivation(message: types.Message):
    await message.answer("Не забывай: каждый шаг к цели — это успех!\n"
                         "Запиши свои цели, чтобы не потерять мотивацию.\n"
                         "Цитата: \"Секрет успеха в том, чтобы начать!\"")

@dp.message(lambda message: message.text == "Диета")
async def send_diet_tracker(message: types.Message):
    await message.answer("Отслеживайте свой рацион, записывая, что вы едите. "
                         "Попробуйте вести дневник питания и отмечать свои чувства после еды.")

@dp.message(lambda message: message.text == "Советы по здоровью")
async def send_health_tips(message: types.Message):
    await message.answer("Полезные советы для здоровья:\n"
                         "- Пейте больше воды\n"
                         "- Двигайтесь каждый день\n"
                         "- Сон не менее 7-8 часов\n"
                         "- Правильное питание — залог хорошего самочувствия!")

@dp.message(lambda message: message.text == "Прогресс")
async def send_progress_tips(message: types.Message):
    await message.answer("Как отслеживать свой прогресс:\n"
                         "- Делайте замеры тела раз в неделю\n"
                         "- Ведите дневник тренировок\n"
                         "- Используйте фото до/после\n"
                         "- Следите за своим самочувствием, а не только за цифрами на весах!")

@dp.message(lambda message: message.text == "Рецепты")
async def send_recipes(message: types.Message):
    await message.answer("Вот несколько полезных рецептов:\n"
                         "1. Овсянка с ягодами и орехами\n"
                         "2. Куриная грудка с овощами на пару\n"
                         "3. Смузи из банана, шпината и миндального молока\n"
                         "4. Творожный десерт с медом и орехами")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
