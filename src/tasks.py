import io
import logging

import boto3
from celery import Celery
from envparse import env
from sentry_sdk.integrations.celery import CeleryIntegration
from telegram import Bot

from .scrapinghub_helper import WbCategoryComparator, WbCategoryStats, wb_category_export

env.read_envfile()

celery = Celery('tasks')
celery.conf.update(
    broker_url=env('REDIS_URL'),
    task_always_eager=env('CELERY_ALWAYS_EAGER', cast=bool, default=False),
    task_serializer='pickle',  # we transfer binary data like photos or voice messages,
    accept_content=['pickle'],
)

# включаем логи
logger = logging.getLogger(__name__)

bot = Bot(env('TELEGRAM_API_TOKEN'))
s3 = boto3.client('s3')


def get_cat_update_users():
    return env('WILDSEARCH_TEST_USER_LIST').split(',')


@celery.task()
def calculate_wb_category_diff():
    comparator = WbCategoryComparator()
    comparator.load_from_api()
    comparator.calculate_diff()

    added_count = comparator.get_categories_count('added')
    removed_count = comparator.get_categories_count('removed')

    added_unique_count = comparator.get_categories_unique_count('added')

    if added_unique_count == 0:
        message = f'За последние сутки на Wildberries не добавилось категорий'
        files = None
    else:
        comparator.dump_to_s3_file('added')
        comparator.dump_to_s3_file('removed')
        files = [
            comparator.get_s3_file_name('added'),
            comparator.get_s3_file_name('removed'),
        ]

        message = f'Обновились данные по категориям на Wildberries. C последнего  обновления добавилось ' \
                  f'{added_count} категорий, из них {added_unique_count} уникальных. Скрылось ' \
                  f'{removed_count} категорий'

    for uid in get_cat_update_users():
        send_wb_category_update_message.delay(uid, message, files)


@celery.task()
def calculate_wb_category_stats(job_id, chat_id):
    stats = WbCategoryStats().fill_from_api(job_id)

    message = f'[{stats.get_category_name()}]({stats.get_category_url()})\n' \
              f'\n' \
              f'Количество товаров: `{stats.get_goods_count()}`\n' \
              f'\n' \
              f'Самый дорогой: `{"{:,}".format(stats.get_goods_price_max())}` руб.\n' \
              f'Самый дешевый: `{"{:,}".format(stats.get_goods_price_min())}` руб.\n' \
              f'Средняя цена: `{"{:,}".format(stats.get_goods_price_mean())}` руб.\n' \
              f'\n' \
              f'Объем продаж: `{"{:,}".format(stats.get_sales_sum())}` руб.\n' \
              f'Средние продажи: `{"{:,}".format(stats.get_sales_mean())}` руб.\n' \
              f'Медиана продаж: `{"{:,}".format(stats.get_sales_median())}` руб.\n'

    bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

    bot.send_document(chat_id=chat_id, document=stats.get_category_excel(), filename=f'{stats.get_category_name()} на Wildberries.xlsx')


@celery.task()
def schedule_wb_category_export(category_url, chat_id):
    try:
        job_url = wb_category_export(category_url, chat_id)
        message = f"Я поставил каталог в очередь на исследование. Скоро пришлю результаты."
    except Exception as e:
        message = f"Произошла ошибка при запросе каталога, попробуйте запросить его позже"

        pass

    bot.send_message(chat_id=chat_id, text=message)


@celery.task()
def send_wb_category_update_message(uid, message, files=None):
    if files is None:
        files = []

    bot.send_message(chat_id=uid, text=message)

    for file_name in files:
        f = io.BytesIO()
        s3.download_fileobj(env('AWS_S3_BUCKET_NAME'), file_name, f)
        f.seek(0, 0)
        bot.send_document(chat_id=uid, document=f, filename=file_name)
