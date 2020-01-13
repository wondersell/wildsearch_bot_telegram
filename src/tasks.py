import sentry_sdk
import boto3
import tempfile
import logging
import io
from celery import Celery
from envparse import env
from sentry_sdk.integrations.celery import CeleryIntegration
from telegram import Bot

from .scrapinghub_helper import WbCategoryComparator, category_export

env.read_envfile()

celery = Celery('tasks')
celery.conf.update(
    broker_url=env('REDIS_URL'),
    task_always_eager=env('CELERY_ALWAYS_EAGER', cast=bool, default=False),
    task_serializer='pickle',  # we transfer binary data like photos or voice messages,
    accept_content=['pickle'],
)

# включаем логи
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

if env('SENTRY_DSN', default=None) is not None:
    sentry_sdk.init(env('SENTRY_DSN'), integrations=[CeleryIntegration()])

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
def schedule_category_export(category_url, chat_id):
    try:
        job_url = category_export(category_url, chat_id)
        message = f"Вы запросили анализ каталога, он будет доступен по ссылке {job_url}"
        bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        message = f"Произошла ошибка при запросе каталога, попробуйте запросить его позже"
        bot.send_message(chat_id=chat_id, text=message)
        pass


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
