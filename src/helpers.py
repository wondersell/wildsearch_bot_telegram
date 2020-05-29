import json
import logging
import re

import boto3
import requests
from envparse import env
from scrapinghub import ScrapinghubClient
from seller_stats.transformers import WildsearchCrawlerOzonTransformer as ozon_transformer
from seller_stats.transformers import WildsearchCrawlerWildberriesTransformer as wb_transformer

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

    return None, None


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
        'callback_url': env('WILDSEARCH_JOB_FINISHED_CALLBACK') + '/category_export',
        'callback_params': f'chat_id={chat_id}',
    })

    logger.info(f'Export for category {url} will have job key {job.key}')
    return 'https://app.scrapinghub.com/p/' + job.key
