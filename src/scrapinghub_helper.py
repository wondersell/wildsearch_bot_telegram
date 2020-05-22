import logging

import boto3
from envparse import env
from scrapinghub import ScrapinghubClient

logger = logging.getLogger(__name__)

# инициализируем S3
s3 = boto3.client('s3')


def init_scrapinghub():
    logger.info('Initializing scrapinghub')
    client = ScrapinghubClient(env('SH_APIKEY'))
    project = client.get_project(env('SH_PROJECT_ID'))

    return client, project


def scheduled_jobs_count(project, spider) -> int:
    spider = project.spiders.get(spider)
    return spider.jobs.count(state='pending') + spider.jobs.count(state='running')


def wb_category_export(url, chat_id) -> str:
    """Schedule WB category export on Scrapinghub."""
    logger.info(f'Export {url} for chat #{chat_id}')
    client, project = init_scrapinghub()

    if scheduled_jobs_count(project, 'wb') > env('SCHEDULED_JOBS_THRESHOLD', cast=int, default=1):
        raise Exception('Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs')

    job = project.jobs.run('wb', job_args={
        'category_url': url,
        'callback_url': env('WILDSEARCH_JOB_FINISHED_CALLBACK') + '/wb_category_export',
        'callback_params': f'chat_id={chat_id}',
    })

    logger.info(f'Export for category {url} will have job key {job.key}')
    return 'https://app.scrapinghub.com/p/' + job.key
