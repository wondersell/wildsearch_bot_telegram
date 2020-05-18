import logging
import tempfile

import boto3
import pandas as pd
from celery import Celery
from envparse import env
from seller_stats.category_stats import CategoryStats
from seller_stats.formatters import format_currency as fcur
from seller_stats.formatters import format_number as fnum
from seller_stats.formatters import format_quantity as fquan
from seller_stats.loaders import ScrapinghubLoader
from seller_stats.transformers import WildsearchCrawlerWildberriesTransformer as wb_transformer
from telegram import Bot

from .amplitude_helper import AmplitudeLogger
from .models import LogCommandItem, get_subscribed_to_wb_categories_updates, user_get_by
from .scrapinghub_helper import wb_category_export

env.read_envfile()

celery = Celery('tasks')
celery.conf.update(
    broker_url=env('REDIS_URL'),
    task_always_eager=env('CELERY_ALWAYS_EAGER', cast=bool, default=False),
    task_serializer='pickle',  # we transfer binary data like photos or voice messages,
    accept_content=['pickle'],
    redis_max_connections=env('CELERY_REDIS_MAX_CONNECTIONS', default=None),
)

# включаем логи
logger = logging.getLogger(__name__)

# включаем Amplitude
if env('AMPLITUDE_API_KEY', default=None) is not None:
    amplitude = AmplitudeLogger(env('AMPLITUDE_API_KEY'))

bot = Bot(env('TELEGRAM_API_TOKEN'))
s3 = boto3.client('s3')


def get_cat_update_users():
    users = get_subscribed_to_wb_categories_updates()
    return list(map(lambda x: x.chat_id, users))


@celery.task()
def calculate_wb_category_stats(job_id, chat_id):
    data = ScrapinghubLoader(job_id=job_id, transformer=wb_transformer()).load()
    stats = CategoryStats(data=data)

    stats.calculate_monthly_stats()

    message = generate_category_stats_message(stats=stats)
    bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True)

    export_file = generate_category_stats_file(stats)
    bot.send_document(
        chat_id=chat_id,
        document=export_file,
        filename=f'{stats.category_name()} на Wildberries.xlsx',
    )

    send_category_requests_count_message.delay(chat_id)
    track_amplitude.delay(chat_id=chat_id, event='Received WB category analyses')


@celery.task()
def schedule_wb_category_export(category_url: str, chat_id: int, log_id):
    log_item = LogCommandItem.objects(id=log_id).first()

    try:
        wb_category_export(category_url, chat_id)
        message = '⏳ Мы обрабатываем ваш запрос. Когда все будет готово, вы получите результат.\n\nБольшие категории (свыше 1 тыс. товаров) могут обрабатываться до одного часа.\n\nМаленькие категории обрабатываются в течение нескольких минут.'
        check_requests_count_recovered.apply_async((), {'chat_id': chat_id}, countdown=24 * 60 * 60 + 60)
        log_item.set_status('success')
    except Exception as e:
        message = 'Извините, мы сейчас не можем обработать ваш запрос – у нас образовалась слишком большая очередь на анализ категорий. Пожалуйста, подождите немного и отправьте запрос снова.'
        track_amplitude.delay(chat_id=chat_id, event='Received "Too long queue" error')
        pass

    bot.send_message(chat_id=chat_id, text=message)


@celery.task()
def send_category_requests_count_message(chat_id: int):
    user = user_get_by(chat_id=chat_id)

    emojis_left = ''.join(map(lambda x: '🌕', range(user.catalog_requests_left_count())))
    emojis_used = ''.join(map(lambda x: '🌑', range(user.today_catalog_requests_count())))
    emojis = emojis_left + emojis_used

    message = f'Вам доступно {user.catalog_requests_left_count()} из {user.daily_catalog_requests_limit} запросов\n{emojis}\n\nЛимит восстанавится через 24 часа с момента анализа.'

    bot.send_message(chat_id=chat_id, text=message)


@celery.task()
def check_requests_count_recovered(chat_id: int):
    user = user_get_by(chat_id=chat_id)

    if user.catalog_requests_left_count() == user.daily_catalog_requests_limit:
        # here we are limiting the maximum number of emojis to 10
        # emoji = ''.join(map(lambda x: '🌕', range(min(user.daily_catalog_requests_limit, 10))))
        # message = f'🤘 Рок-н-ролл! Вам доступно {user.daily_catalog_requests_limit} новых запросов категорий Wildberries для анализа.\n{emoji}'
        # bot.send_message(chat_id=chat_id, text=message)

        logger.info('Placeholder for sending recovered requests messages called')


@celery.task()
def track_amplitude(chat_id: int, event: str, event_properties=None, timestamp=None):
    if amplitude:
        user = user_get_by(chat_id=chat_id)
        amplitude.log(
            user_id=chat_id,
            event=event,
            user_properties={
                'Telegram chat ID': user.chat_id,
                'Name': user.full_name,
                'Telegram user name': user.user_name,
                'Daily catalog request limit': user.daily_catalog_requests_limit,
                'Subscribed to WB categories updates': user.subscribe_to_wb_categories_updates,
            },
            event_properties=event_properties,
            timestamp=timestamp,
        )


def generate_category_stats_message(stats):
    df = stats.df

    return f"""
[{stats.category_name()}]({stats.category_url()})

Количество товаров: `{fnum(df.sku.sum())}`

Самый дорогой: {fcur(df.price.max())}
Самый дешевый: {fcur(df.price.min())}
Средняя цена: {fcur(df.price.mean())}

Продаж всего: {fquan(df.purchases.sum())} (на {fcur(df.turnover.sum())})
В среднем продаются по: {fquan(df.purchases.mean())} (на {fcur(df.turnover.mean())})
Медиана продаж: {fquan(df.purchases.median())} (на {fcur(df.turnover.median())})
"""


def generate_category_stats_file(stats):
    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', prefix='wb_category_', mode='r+b', delete=True)

    writer = pd.ExcelWriter(temp_file.name)
    stats.df.to_excel(writer, sheet_name='Товары', index=None, header=True)
    stats.price_distribution().to_excel(writer, sheet_name='Распределение продаж', index=None, header=True)
    writer.save()

    return temp_file
