import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

recipes_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Овсянка с ягодами и орехами")],
        [KeyboardButton(text="Куриная грудка с овощами на пару")],
        [KeyboardButton(text="Смузи из банана, шпината и миндального молока")],
        [KeyboardButton(text="Творожный десерт с медом и орехами")],
        [KeyboardButton(text="Назад в меню")],
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
    await message.answer(
        "Мотивация — это ключ к успеху! Вот несколько советов, которые могут тебе помочь:\n"
        "- Постоянство в действиях — главная составляющая успеха.\n"
        "- Ставь конкретные цели и записывай их.\n"
        "- Не бойся неудач — каждый шаг в любом случае приближает тебя к успеху.\n"
        "Цитата дня: \"Самый трудный шаг — это начало, все остальное проще!\""
    )

@dp.message(lambda message: message.text == "Диета")
async def send_diet(message: types.Message):
    await message.answer(
        "Диета — это не временные ограничения, а способ поддержания здоровья и энергии.\n"
        "Вот несколько советов для здорового питания:\n"
        "- Разделяй прием пищи на 5-6 небольших приемов пищи в течение дня.\n"
        "- Пей много воды — это способствует метаболизму и улучшает пищеварение.\n"
        "- Включай в рацион больше овощей и фруктов.\n"
        "- Ограничь потребление сахара и простых углеводов.\n"
        "Запомни, что здоровая диета — это не диета на неделю, а образ жизни!"
    )

@dp.message(lambda message: message.text == "Советы по здоровью")
async def send_health_tips(message: types.Message):
    await message.answer(
        "Вот несколько простых и полезных советов для поддержания здоровья:\n"
        "- Пей достаточное количество воды каждый день (2-3 литра в зависимости от веса).\n"
        "- Занимайся физической активностью хотя бы 30 минут в день.\n"
        "- Спи не менее 7-8 часов — хороший сон способствует восстановлению организма.\n"
        "- Следи за уровнем стресса и отдыхай, когда это необходимо.\n"
        "- Не забывай про регулярные медицинские осмотры для предотвращения заболеваний."
    )

@dp.message(lambda message: message.text == "Рецепты")
async def send_recipes(message: types.Message):
    await message.answer(
        "Выбери рецепт, чтобы получить подробности:",
        reply_markup=recipes_keyboard
    )

@dp.message(lambda message: message.text == "Овсянка с ягодами и орехами")
async def recipe_1(message: types.Message):
    await message.answer(
        "Овсянка с ягодами и орехами:\n"
        "Ингредиенты:\n"
        "- Овсянка — 100 г\n"
        "- Ягоды (любые) — 50 г\n"
        "- Орехи (миндаль, грецкие) — 20 г\n"
        "- Мед — 1 ч.л.\n"
        "Приготовление:\n"
        "1. Сварите овсянку.\n"
        "2. Добавьте ягоды и орехи.\n"
        "3. Полейте медом для сладости.\n"
        "Приятного аппетита!"
    )

@dp.message(lambda message: message.text == "Куриная грудка с овощами на пару")
async def recipe_2(message: types.Message):
    await message.answer(
        "Куриная грудка с овощами на пару:\n"
        "Ингредиенты:\n"
        "- Куриная грудка — 200 г\n"
        "- Брокколи — 100 г\n"
        "- Морковь — 1 шт.\n"
        "- Соль, перец по вкусу\n"
        "Приготовление:\n"
        "1. Куриную грудку отварить или запечь.\n"
        "2. Овощи порезать и готовить на пару до мягкости.\n"
        "3. Сервировать курицу с овощами. Приятного аппетита!"
    )

# Хэндлер для кнопки Смузи из банана, шпината и миндального молока
@dp.message(lambda message: message.text == "Смузи из банана, шпината и миндального молока")
async def recipe_3(message: types.Message):
    await message.answer(
        "Смузи из банана, шпината и миндального молока:\n"
        "Ингредиенты:\n"
        "- Банан — 1 шт.\n"
        "- Шпинат — 50 г\n"
        "- Миндальное молоко — 200 мл\n"
        "Приготовление:\n"
        "1. Все ингредиенты положить в блендер.\n"
        "2. Взбить до однородной массы.\n"
        "3. Подавать холодным. Приятного аппетита!"
    )

@dp.message(lambda message: message.text == "Творожный десерт с медом и орехами")
async def recipe_4(message: types.Message):
    await message.answer(
        "Творожный десерт с медом и орехами:\n"
        "Ингредиенты:\n"
        "- Творог — 100 г\n"
        "- Мед — 1 ч.л.\n"
        "- Орехи (грецкие, миндаль) — 20 г\n"
        "Приготовление:\n"
        "1. Смешать творог с медом.\n"
        "2. Посыпать орехами.\n"
        "3. Подаем в качестве легкого десерта."
    )

@dp.message(lambda message: message.text == "Назад в меню")
async def back_to_main_menu(message: types.Message):
    await message.answer(
        "Вы вернулись в основное меню.",
        reply_markup=keyboard
    )

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
