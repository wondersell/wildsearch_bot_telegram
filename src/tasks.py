import datetime
import logging
import os
import tempfile
import time

import boto3
import pandas as pd
from airtable import Airtable
from celery import Celery
from envparse import env
from seller_stats.category_stats import CategoryStats, calc_sales_distribution
from seller_stats.exceptions import BadDataSet, NotReady
from seller_stats.utils.formatters import format_currency as fcur
from seller_stats.utils.formatters import format_number as fnum
from seller_stats.utils.formatters import format_quantity as fquan
from seller_stats.utils.loaders import ScrapinghubLoader
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

from .helpers import AmplitudeLogger, category_export, detect_mp_by_job_id
from .models_peewee import LogCommandItem, get_subscribed_to_wb_categories_updates, user_get_by_chat_id

env.read_envfile()

celery = Celery('tasks')
celery.conf.update(
    broker_url=env('REDIS_URL'),
    task_always_eager=env('CELERY_ALWAYS_EAGER', cast=bool, default=False),
    task_serializer='pickle',  # we transfer binary data like photos or voice messages,
    accept_content=['pickle'],
    redis_max_connections=env('CELERY_REDIS_MAX_CONNECTIONS', default=None),
    broker_transport_options={'visibility_timeout': 3600 * 48},
    timezone=env('TIME_ZONE', cast=str, default='Europe/Moscow'),
)

# включаем логи
logger = logging.getLogger(__name__)

bot = Bot(env('TELEGRAM_API_TOKEN'))
s3 = boto3.client('s3')


def get_cat_update_users():
    users = get_subscribed_to_wb_categories_updates()
    return list(map(lambda x: x.chat_id, users))


@celery.task(bind=True, default_retry_delay=10, max_retries=6)
def calculate_category_stats(self, job_id, chat_id):
    user = user_get_by_chat_id(chat_id=chat_id)
    slug, marketplace, transformer = detect_mp_by_job_id(job_id=job_id)
    data = []

    try:
        data = ScrapinghubLoader(job_id=job_id, transformer=transformer).load()
    except NotReady:
        logger.error(f'Job {job_id} is not finished yet, placing new task')
        self.retry()

    try:
        stats = CategoryStats(data=data)
    except BadDataSet:
        bot.send_message(chat_id=chat_id, text='❌ Мы не смогли обработать ссылку. Скорее всего, вы указали неправильную страницу, либо категория оказалась пустой.',
                         parse_mode='Markdown', disable_web_page_preview=True)
        logger.error(f'Job {job_id} returned empty category')
        return

    message = generate_category_stats_message(stats=stats)
    bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True)

    # export_file = generate_category_stats_export_file(stats)
    export_file = generate_category_stats_report_file(stats, username=user.user_name)

    filename, file_extension = os.path.splitext(export_file.name)

    try:
        bot.send_document(
            chat_id=chat_id,
            document=export_file,
            caption='Файл с отчетом',
            filename=f'{stats.category_name()} на {marketplace}.{file_extension}',
        )
    except Exception as exception_info:
        logger.error(f'Error while sending file: {str(exception_info)}')
        pass

    send_category_requests_count_message.delay(chat_id)
    track_amplitude.delay(chat_id=chat_id, event=f'Received {slug} category analyses')


@celery.task()
def schedule_category_export(category_url: str, chat_id: int, log_id):
    log_item = LogCommandItem.get(LogCommandItem.id == log_id)

    try:
        category_export(category_url, chat_id)
        message = '⏳ Мы обрабатываем ваш запрос. Когда все будет готово, вы получите результат.\n\nБольшие категории (свыше 1 тыс. товаров) могут обрабатываться до одного часа.\n\nМаленькие категории обрабатываются в течение нескольких минут.'
        check_requests_count_recovered.apply_async((), {'chat_id': chat_id}, countdown=24 * 60 * 60 + 60)
        log_item.set_status('success')
    except Exception:
        message = 'Извините, мы сейчас не можем обработать ваш запрос – у нас образовалась слишком большая очередь на анализ категорий. Пожалуйста, подождите немного и отправьте запрос снова.'
        track_amplitude.delay(chat_id=chat_id, event='Received "Too long queue" error')
        log_item.set_status('too_long_queue')
        pass

    bot.send_message(chat_id=chat_id, text=message)


@celery.task()
def send_category_requests_count_message(chat_id: int):
    user = user_get_by_chat_id(chat_id=chat_id)

    requests_left = user.catalog_requests_left_count()
    requests_today = user.today_catalog_requests_count()

    if (requests_left + requests_today) <= 10:
        emojis_left = ''.join(map(lambda x: '🌕', range(requests_left)))
        emojis_used = ''.join(map(lambda x: '🌑', range(requests_today)))
        emojis = emojis_left + emojis_used + '\n\n'
    else:
        emojis = ''

    if requests_left > 0:
        message = f'Вам доступно {requests_left} из {user.daily_catalog_requests_limit} запросов\n{emojis}Лимит восстанавится через 24 часа с момента анализа.'
        reply_markup = None
    else:
        message = f'У вас больше нет доступных запросов.\n{emojis}\n\nВы можете снять ограничения, купив платный аккаунт. Либо подождите 24 часа и лимит восстановится.'
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton('🚀 Снять ограничения', callback_data='keyboard_help_no_limits')],
        ])

    bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


@celery.task()
def check_requests_count_recovered(chat_id: int):
    user = user_get_by_chat_id(chat_id=chat_id)

    if user.catalog_requests_left_count() == user.daily_catalog_requests_limit:
        # here we are limiting the maximum number of emojis to 10
        # emoji = ''.join(map(lambda x: '🌕', range(min(user.daily_catalog_requests_limit, 10))))
        # message = f'🤘 Рок-н-ролл! Вам доступно {user.daily_catalog_requests_limit} новых запросов категорий Wildberries для анализа.\n{emoji}'
        # bot.send_message(chat_id=chat_id, text=message)

        # track_amplitude.delay(chat_id=chat_id, event='Received "Recovered requests" message')
        logger.info('Placeholder for Recovered requests messages called')


@celery.task()
def track_amplitude(chat_id: int, event: str, event_properties=None, timestamp=None):
    if env('AMPLITUDE_API_KEY', default=None) is not None:
        amplitude = AmplitudeLogger(env('AMPLITUDE_API_KEY'))
        user = user_get_by_chat_id(chat_id=chat_id)
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
Ваш PDF-отчет по категории [{stats.category_name()}]({stats.category_url()}) находится в следующем сообщении.

Краткая сводка:
Количество товаров: `{fnum(df.sku.sum())}`
Продаж всего: {fquan(df.purchases.sum())} (на {fcur(df.turnover.sum())})
В среднем продаются по: {fquan(df.purchases.mean())} (на {fcur(df.turnover.mean())})
Медиана продаж: {fquan(df.purchases.median())} (на {fcur(df.turnover.median())})
"""


def generate_category_stats_export_file(stats):
    start_time = time.time()

    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', prefix='wb_category_', mode='r+b', delete=True)

    writer = pd.ExcelWriter(temp_file.name)
    stats.df.to_excel(writer, sheet_name='Товары', index=None, header=True)

    distributions = calc_sales_distribution(stats)
    distributions.df.to_excel(writer, sheet_name='Распределение продаж', index=None, header=True)
    writer.save()

    logger.info(f'Export file generated in {time.time() - start_time}s, {os.path.getsize(temp_file.name)} bytes')

    return temp_file


def generate_category_stats_report_file(stats, username='%username%'):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from weasyprint import HTML
    from .viewmodels.report import Report

    start_time = time.time()

    base_path = os.path.dirname(os.path.abspath(__file__)) + '/templates/pdf/report/'
    environment = Environment(
        loader=FileSystemLoader(base_path),
        autoescape=select_autoescape(['html', 'xml']),
    )
    template = environment.get_template('_index.j2')

    temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', prefix='wb_category_', mode='w+b', delete=False)
    report_vm = Report(stats=stats, username=username)

    HTML(string=template.render(report_vm.to_dict()), base_url=f'{base_path}').write_pdf(target=temp_file.name)

    logger.info(f'PDF report generated in {time.time() - start_time}s, {os.path.getsize(temp_file.name)} bytes')

    return temp_file


def add_user_to_crm(chat_id):
    if env('AIRTABLE_API_KEY', None) is not None:
        logger.info('Saving new user to CRM')

        user = user_get_by_chat_id(chat_id=chat_id)

        logger.info(f"created_at is {user.created_at.replace(tzinfo=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')}")

        airtable = Airtable(env('AIRTABLE_BASE_KEY'), env('AIRTABLE_CRM_TABLE'), api_key=env('AIRTABLE_API_KEY'))
        airtable.insert({
            'Имя': user.full_name,
            'Юзернейм': user.user_name,
            'ID чата': user.chat_id,
            'Зарегистрирован': user.created_at.replace(tzinfo=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        })
