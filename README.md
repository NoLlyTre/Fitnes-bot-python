# BodyIsFine // @BodyIsFine_bot
Этот проект представляет собой фитнес-бота, разработанного с использованием библиотеки Aiogram для Telegram. Бот помогает пользователям отслеживать их физическую активность, диету и прогресс в достижении фитнес-целей. Он также предоставляет мотивационные цитаты и рецепты здорового питания. 🏋️‍♂️😊

## Функциональные возможности
Мотивация: Бот предлагает вдохновляющие цитаты и советы по мотивации. 💪

Диета: Пользователи получают советы по здоровому питанию и диетам. 🥗

Советы по здоровью: Полезные рекомендации для поддержания здоровья. 🩺

Прогресс: Возможность отслеживания веса, приема пищи и калорий. 📊

Рецепты: Предложение различных рецептов в зависимости от целей пользователя (похудение или набор массы). 🍽️

## Установка
Требования

Python: 3.7 или выше
Библиотеки:
aiogram

aiosqlite

plotly

## Установка зависимостей
pip install aiogram aiosqlite plotly

## Настройка базы данных
Перед запуском бота необходимо создать базу данных. Бот автоматически создаст необходимые таблицы при первом запуске. 🗄️

## Запуск
Сохраните токен вашего бота, полученный от BotFather, в переменной TOKEN в коде.
Запустите бота:
python your_bot_file.py
## Использование
После запуска бота отправьте команду /start, чтобы получить приветственное сообщение и меню с доступными функциями. 🎉

Выберите желаемую опцию, используя кнопки, чтобы взаимодействовать с ботом.

Бот будет запрашивать ввод данных, таких как вес, калории и информация о приеме пищи. 📝

## Структура базы данных
База данных состоит из следующих таблиц:

users: Хранит информацию о пользователях, включая их целевые калории и предпочтения. 👤

weight_records: Записывает вес пользователей с указанием даты. ⚖️

meal_records: Хранит информацию о приеме пищи, включая тип и калории. 🍏

## Логирование
Бот настроен на ведение логов, которые сохраняются в файл bot.log. Логи содержат информацию о действиях бота, ошибках и других событиях. 📜

## Примечания
Убедитесь, что файл quotes.txt с мотивационными цитатами находится в том же каталоге, что и скрипт, чтобы бот мог их использовать. 📂
Бот использует режим WAL для базы данных SQLite для повышения производительности. 🚀
Включена защита от частых запросов с помощью middleware, чтобы избежать перегрузки. ⚠️
## Лицензия
Этот проект лицензирован на условиях MIT License. Вы можете свободно использовать, изменять и распространять его, но с указанием авторства. 📄

Если у вас есть вопросы или предложения по улучшению, не стесняйтесь обращаться! Мы всегда рады помочь и услышать ваши идеи! 😊

## Контакты
Если у вас возникли вопросы или вам нужна помощь, вы можете связаться с нами по следующим каналам:

Email: позже 📧
Telegram: позже 📱
## Вклад в проект
Если вы хотите внести свой вклад в развитие фитнес-бота, вы можете сделать следующее:

Сообщить об ошибках: Если вы нашли баг или ошибку, пожалуйста, создайте issue на GitHub. 🐛
Предложить новые функции: У вас есть идея для новой функции? Мы будем рады услышать ваши предложения! 💡
Отправить пулл-реквест: Если вы хотите внести изменения в код, создайте пулл-реквест с вашими улучшениями. 🔄
## Планы на будущее
Мы планируем добавить в бота следующие функции:

Интеграция с носимыми устройствами (фитнес-трекерами). ⌚
Расширенные возможности отслеживания прогресса (графики и статистика). 📈
Поддержка нескольких языков для более широкой аудитории. 🌍
