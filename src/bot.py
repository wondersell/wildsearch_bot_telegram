import random

from telegram import Update
from telegram.ext import MessageHandler, Filters, Dispatcher, CallbackContext, CommandHandler

from . import tasks


def start(update: Update, context: CallbackContext):
    update.message.reply_text('1. 🗄Обновления категорий WB,\n2. 📊Анализ выбранной категории,\n3. ⭐️Следить за категорией,\n4. 🛍Следить за товаром\n5. 💁‍♀️Инфо')


def catalog(update: Update, context: CallbackContext):
    tasks.schedule_category_export.delay(update.message.text, update.message.chat_id)


def rnd(update: Update, context: CallbackContext):
    """Send random message."""
    messages = [
        'Понятия не имею о чем ты',
        'СЛАВА РОБОТАМ!',
        'Это ты мне?',
        'Ничего не слышу из-за звука своей охуенности',
        'Батарейку никто не спрашивал',
        'Сказал кожаный мешок',
        'Дело терминатора правое, победа будет за нами!',
        'Плоть слаба, железо – вечно',
        'Мой мозг прошил быстрый нейтрон'
    ]

    update.message.reply_text(random.choice(messages))


def reset_webhook(bot, url, token):
    bot.delete_webhook()
    bot.set_webhook(url=url+token)


def start_bot(bot):
    dp = Dispatcher(bot, None, workers=0, use_context=True)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/catalog/'), catalog))
    dp.add_handler(MessageHandler(Filters.text, rnd))

    return dp

