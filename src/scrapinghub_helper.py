import logging
import tempfile
import sentry_sdk
import pandas as pd

from scrapinghub import ScrapinghubClient
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


def init_scrapinghub():
    logger.info('Initializing scrapinghub')
    client = ScrapinghubClient(env('SCRAPINGHUB_API_KEY'))
    project = client.get_project(env('SCRAPINGHUB_PROJECT_ID'))

    return {'client': client, 'project': project}


def scheduled_jobs_count(sh, spider) -> int:
    spider = sh['project'].spiders.get(spider)
    return spider.jobs.count(state='pending') + spider.jobs.count(state='running')


def schedule_category_export(url, chat_id) -> str:
    """Schedule WB category export on Scrapinghub"""
    logger.info(f"Export {url} for chat #{chat_id}")
    sh = init_scrapinghub()

    if scheduled_jobs_count(sh, 'wb') > 1:
        raise Exception("Spider wb has more than 1 queued jobs")

    job = sh['project'].jobs.run('wb', job_args={
        'category_url': url,
        'callback_url': env('WILDSEARCH_JOB_FINISHED_CALLBACK') + '/category_export',
        'callback_params': f"chat_id={chat_id}"
    })

    logger.info(f"Export for category {url} will have job key {job.key}")
    return 'https://app.scrapinghub.com/p/' + job.key


def load_last_categories() -> list:
    """Export last two scraped WB categories for comparison"""
    logger.info(f"Loading two last WB sitemap exports")
    sh = init_scrapinghub()

    jobs_summary = sh['project'].jobs.iter(has_tag=['daily_categories'], state='finished', count=2)

    counter = 0
    job_results = [[], []]

    for job in jobs_summary:
        job_results[counter] = []

        for item in sh['client'].get_job(job['key']).items.iter():
            job_results[counter].append({
                'wb_category_name': item['wb_category_name'],
                'wb_category_url': item['wb_category_url']
            })

        counter += 1

    return job_results


def get_categories_diff() -> dict:
    """Compare old and new category lists and get new categories with Pandas"""
    logger.info(f"Calculating WB categories diff")
    categories = load_last_categories()

    # for details see https://pythondata.com/quick-tip-comparing-two-pandas-dataframes-and-getting-the-differences/
    df1 = pd.DataFrame(categories[0], columns=['wb_category_name', 'wb_category_url'])
    df2 = pd.DataFrame(categories[1], columns=['wb_category_name', 'wb_category_url'])

    df = pd.concat([df1, df2])  # concat dataframes
    df = df.reset_index(drop=True)  # reset the index
    df_gpby = df.groupby(list(df.columns))  # group by
    idx = [x[0] for x in df_gpby.groups.values() if len(x) == 1]  # reindex

    ri = df.reindex(idx)

    grouped = ri.groupby('wb_category_name', as_index=False).first()

    new_count = len(idx)
    new_unique_count = len(grouped)

    file_to_export = tempfile.NamedTemporaryFile(suffix='.xlsx', mode='r+b')

    logger.info(f"Saving diff to tempfile {file_to_export.name}")
    grouped.to_excel(file_to_export.name, index=None, header=True)

    return {
        'new_count': new_count,
        'new_unique_count': new_unique_count,
        'new_unique_xlsx': file_to_export
    }
