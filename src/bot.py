import logging
import random
import os
import sentry_sdk

from .scrapinghub_helper import *
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from envparse import env


# загружаем конфиг
env.read_envfile()

# включаем логи
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# включаем Sentry
if env('SENTRY_DSN', default=None) is not None:
    sentry_sdk.init(env('SENTRY_DSN'))


def catalog(update, context):
    logger.info(f"Received request for catalog info ({update.message.text})")

    job_url = schedule_category_export(update.message.text, update.message.chat_id)

    update.message.reply_text(f"Вы запросили анализ каталога, он будет доступен по ссылке {job_url}")


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def rnd(update, context):
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


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot"""
    updater = Updater(env('TELEGRAM_API_TOKEN'), use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on catalog link start exporting catalog data
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/catalog/'), catalog))

    # on no command i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, rnd))

    # log all errors
    dp.add_error_handler(error)

    if env('WILDSEARCH_USE_WEBHOOKS'):
        logger.info('User webhooks param is ON, setting webhooks')

        updater.start_webhook(listen="0.0.0.0",
                              port=int(os.environ.get('PORT', '8443')),
                              url_path=env('TELEGRAM_API_TOKEN'))
        updater.bot.set_webhook(env('WILDSEARCH_WEBHOOKS_DOMAIN') + env('TELEGRAM_API_TOKEN'))
    else:
        logger.info('User webhooks param is OFF, deleting webhooks and starting longpolling')
        updater.bot.delete_webhook()
        updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
