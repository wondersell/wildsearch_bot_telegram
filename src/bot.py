import random
import logging

from telegram import Update
from telegram.ext import MessageHandler, Filters, Dispatcher, CallbackContext, CommandHandler
from .models import *

from . import tasks

# включаем логи
logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    logger.info('Start command received')
    user = user_get_by_update(update)
    log_command(user, 'start', update.message.text)

    update.message.reply_text(f'Привет, {user.user_name}! Вот возможные команды:\n\n1. 🗄Обновления категорий WB,\n2. 📊Анализ выбранной категории,\n3. ⭐️Следить за категорией,\n4. 🛍Следить за товаром\n5. 💁‍♀️Инфо')


def wb_catalog(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_command(user, 'wb_catalog', update.message.text)

    if user.can_send_more_catalog_requests():
        tasks.schedule_wb_category_export.delay(update.message.text, update.message.chat_id)
    else:
        update.message.reply_text(f'Сорян, у тебя закончился лимит выгрузок на сегодня')


def rnd(update: Update, context: CallbackContext):
    user = user_get_by_update(update)
    log_command(user, 'rnd', update.message.text)

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
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/catalog/'), wb_catalog))
    dp.add_handler(MessageHandler(Filters.text, rnd))

    return dp
