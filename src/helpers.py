import json
import logging
import math
import re

import boto3
import requests
from envparse import env
from scrapinghub import ScrapinghubClient
from seller_stats.utils.transformers import WildsearchCrawlerOzonTransformer as ozon_transformer
from seller_stats.utils.transformers import WildsearchCrawlerWildberriesTransformer as wb_transformer

logger = logging.getLogger(__name__)

# инициализируем S3
s3 = boto3.client('s3')


class AmplitudeLogger:
    def __init__(self, api_key):
        self.api_key = api_key
        self.endpoint = 'https://api.amplitude.com/2/httpapi'

    def log(self, user_id, event, user_properties=None, event_properties=None, timestamp=None):
        amp_event = {
            'user_id': user_id,
            'event_type': event,
            'platform': 'Telegram',
        }

        if user_properties is not None:
            amp_event['user_properties'] = user_properties

        if event_properties is not None:
            amp_event['event_properties'] = event_properties

        if timestamp is not None:
            amp_event['time'] = timestamp

        amp_request = {
            'api_key': self.api_key,
            'events': [
                amp_event,
            ],
        }

        requests.post(self.endpoint, data=json.dumps(amp_request))


def detect_mp_by_job_id(job_id):
    spider = re.findall(r'\d+\/(\d+)\/\d+', job_id)[0]

    if spider == env('SH_WB_SPIDER'):
        return 'WB', 'Wildberries', wb_transformer()

    if spider == env('SH_OZON_SPIDER'):
        return 'Ozon', 'Ozon', ozon_transformer()

    return None, None, None


def init_scrapinghub():
    logger.info('Initializing scrapinghub')
    client = ScrapinghubClient(env('SH_APIKEY'))
    project = client.get_project(env('SH_PROJECT_ID'))

    return client, project


def scheduled_jobs_count(project, spider) -> int:
    spider = project.spiders.get(spider)
    return spider.jobs.count(state='pending') + spider.jobs.count(state='running')


def category_export(url, chat_id, spider='wb') -> str:
    """Schedule WB category export on Scrapinghub."""
    logger.info(f'Export {url} for chat #{chat_id}')
    client, project = init_scrapinghub()

    if scheduled_jobs_count(project, spider) > env('SCHEDULED_JOBS_THRESHOLD', cast=int, default=1):
        raise Exception('Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs')

    job = project.jobs.run(spider, job_args={
        'category_url': url,
        'callback_url': env('WILDSEARCH_JOB_FINISHED_CALLBACK') + f'/{spider}_category_export',
        'callback_params': f'chat_id={chat_id}',
    })

    logger.info(f'Export for category {url} will have job key {job.key}')
    return 'https://app.scrapinghub.com/p/' + job.key


def smart_format_number(number):

    # 10 650 руб.
    # 15 тыс. шт.
    # 53 тыс
    # 1,3 млн. руб.
    # 1,9 млн. руб.
    # 6,8 млн.руб.
    # 22 млн. руб.
    # 41,7 млн. руб.

    # 892 977 678 236 940
    try:
        number = int(number)
    except ValueError:
        return '–', ''

    try:
        rounded, natural = smart_format_round(number)
    except ValueError:
        return '–', ''

    pretty = smart_format_prettify(rounded)
    text_digits = get_digits_text(len(str(number)))

    return pretty, text_digits


def smart_format_round(number) -> (int, int):
    digits = len(str(abs(number)))

    rounded = round(number)
    natural = round(number)

    # 177 -> 180
    if 1 < digits <= 3:
        rounded = round(number / 10) * 10
        natural = rounded

    # 2 112 -> 2 100
    if 3 < digits <= 4:
        rounded = round(number / 100) * 100
        natural = rounded

    # 15 487 -> 15 тыс.
    if 4 < digits <= 6:
        rounded = round(number / 1000)
        natural = rounded * 1000

    # 2 863 578 -> 2,9 млн.
    if 6 < digits <= 8:
        rounded = round(number / 1000000, 1)
        natural = rounded * 1000000

    # 672 934 573 -> 673 млн.
    if 8 < digits <= 9:
        rounded = round(number / 1000000)
        natural = rounded * 1000000

    # 72 691 235 664 -> 72,7 млрд.
    if 9 < digits <= 11:
        rounded = round(number / 1000000000, 1)
        natural = rounded * 1000000000

    # 684 971 367 849 -> 685 млрд.
    if 11 < digits <= 12:
        rounded = round(number / 1000000000)
        natural = rounded * 1000000000

    # 81 235 118 364 583 -> 81,2 трлн.
    if 12 < digits <= 14:
        rounded = round(number / 1000000000000, 1)
        natural = rounded * 1000000000000

    # 811 135 017 356 193 -> 811 трлн.
    if 14 < digits <= 15:
        rounded = round(number / 1000000000000)
        natural = rounded * 1000000000000

    return rounded, natural


def smart_format_round_hard(number) -> (int, int):
    number = round(number)
    digits = len(str(abs(number)))
    remainder = digits % 3

    diveder_degree = 0
    multiplier = 1

    # Числа из одной цифры просто округляем, для остальных делаем так, чтобы они заканчивались на 0
    if remainder == 0 and digits > 1:
        diveder_degree = digits - 2
        multiplier = 10

    if remainder == 1 and digits > 1:
        diveder_degree = digits - 1
        multiplier = 1

    if remainder == 2 and digits > 1:
        diveder_degree = digits - 1
        multiplier = 10

    rounded = round(number / 10 ** diveder_degree) * multiplier
    natural = round(number / 10 ** diveder_degree) * 10 ** diveder_degree

    return rounded, natural


def smart_format_round_super_hard(number) -> (int, int):
    number = round(number)
    digits = len(str(abs(number)))
    remainder = digits % 3

    divider_degree = 0
    multiplier = 1

    # Числа из одной цифры просто округляем, для остальных делаем так, чтобы они заканчивались на 0, округляя вверх
    if remainder == 1 and digits > 1:
        divider_degree = digits - 1
        multiplier = 1

    if remainder == 2 and digits > 1:
        divider_degree = digits - 1
        multiplier = 10

    if remainder == 0 and digits > 1:
        divider_degree = digits - 1
        multiplier = 100

    rounded = math.ceil(number / 10 ** divider_degree) * multiplier
    natural = math.ceil(number / 10 ** divider_degree) * 10 ** divider_degree

    return rounded, natural


def smart_format_prettify(number):
    number = int(number) if float(round(number, 2)) % 1 == 0 else round(float(number), 2)
    number = '{:,}'.format(number).replace(',', ' ').replace('.', ',')

    return number


def get_digits_text(number_length: int, skip_thousands: bool = True) -> str:
    if skip_thousands:
        if 4 < number_length <= 6:
            return 'тыс.'
    else:
        if 3 < number_length <= 6:
            return 'тыс.'

    if 6 < number_length <= 9:
        return 'млн.'

    if 9 < number_length <= 12:
        return 'млрд.'

    if 12 < number_length <= 15:
        return 'трлн.'

    return ''
