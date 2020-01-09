import random
import os
import random

from envparse import env
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .scrapinghub_helper import *

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
    logger.info(f"Requested export ({update.message.text}) for chat #{update.message.chat_id}")

    try:
        job_url = schedule_category_export(update.message.text, update.message.chat_id)
        update.message.reply_text(f"Вы запросили анализ каталога, он будет доступен по ссылке {job_url}")
    except Exception as e:
        logger.error(f"Export for chat #{update.message.chat_id} failed: {str(e)}")
        update.message.reply_text(f"Произошла ошибка при запросе каталога, попробуйте запросить его позже")


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


def main():
    """Start the bot"""
    updater = Updater(env('TELEGRAM_API_TOKEN'), use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on catalog link start exporting catalog data
    dp.add_handler(MessageHandler(Filters.text & Filters.regex('www\.wildberries\.ru/catalog/'), catalog))

    # on no command i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, rnd))

    if env('WILDSEARCH_USE_WEBHOOKS', default=False) is not False:
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
