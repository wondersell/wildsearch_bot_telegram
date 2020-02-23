import logging
import os
import tempfile
from urllib.parse import quote, urlencode, urlunparse

import boto3
import pandas as pd
from envparse import env
from scrapinghub import ScrapinghubClient

logger = logging.getLogger(__name__)

# инициализируем S3
s3 = boto3.client('s3')


def init_scrapinghub():
    logger.info('Initializing scrapinghub')
    client = ScrapinghubClient(env('SCRAPINGHUB_API_KEY'))
    project = client.get_project(env('SCRAPINGHUB_PROJECT_ID'))

    return {'client': client, 'project': project}


def scheduled_jobs_count(sh, spider) -> int:
    spider = sh['project'].spiders.get(spider)
    return spider.jobs.count(state='pending') + spider.jobs.count(state='running')


def wb_category_export(url, chat_id) -> str:
    """Schedule WB category export on Scrapinghub."""
    logger.info(f'Export {url} for chat #{chat_id}')
    sh = init_scrapinghub()

    if scheduled_jobs_count(sh, 'wb') > 1:
        raise Exception('Spider wb has more than 1 queued jobs')

    job = sh['project'].jobs.run('wb', job_args={
        'category_url': url,
        'callback_url': env('WILDSEARCH_JOB_FINISHED_CALLBACK') + '/wb_category_export',
        'callback_params': f'chat_id={chat_id}',
    })

    logger.info(f'Export for category {url} will have job key {job.key}')
    return 'https://app.scrapinghub.com/p/' + job.key


class WbCategoryComparator:
    _columns = ['wb_category_name', 'wb_category_url']
    _types = ['added', 'removed', 'full']

    def fill_types_with(self, value):
        skeleton = {}

        for _t in self._types:
            skeleton[_t] = value

        return skeleton

    def generate_search_url(self, category_name):
        return urlunparse((
            'https',
            'www.wildberries.ru',
            'catalog/0/search.aspx',
            '',
            urlencode({'search': category_name}, quote_via=quote),
            '',
        ))

    def generate_category_type(self, category_url):
        if '/catalog/novinki/' in category_url:
            return 'Новинки'

        if '/promotions/' in category_url:
            return 'Промо'

        return 'Обычная'

    def __init__(self):
        self.categories_old = []
        self.categories_new = []

        self.diff = self.fill_types_with(pd.DataFrame())
        self.diff_unique = self.fill_types_with(pd.DataFrame())
        self.s3_files = self.fill_types_with(None)

    def load_from_api(self):
        """Export last two scraped WB categories for comparison."""
        sh = init_scrapinghub()

        jobs_summary = sh['project'].jobs.iter(has_tag=['daily_categories'], state='finished', count=2)

        counter = 0
        job_results = [[], []]

        for job in jobs_summary:
            job_results[counter] = []

            for item in sh['client'].get_job(job['key']).items.iter():
                job_results[counter].append({
                    'wb_category_name': item['wb_category_name'],
                    'wb_category_url': item['wb_category_url'],
                })

            counter += 1

        self.categories_old = job_results[0]
        self.categories_new = job_results[1]
        return self

    def load_from_list(self, l_1, l_2):
        self.categories_old = l_1
        self.categories_new = l_2
        return self

    def add_category_search_url(self):
        for _type in self._types:
            self.diff[_type]['wb_category_search_url'] = self.diff[_type]['wb_category_name'].apply(
                lambda x: self.generate_search_url(x),
            )

    def add_category_type(self):
        for _type in self._types:
            self.diff[_type]['wb_category_type'] = self.diff[_type]['wb_category_url'].apply(
                lambda x: self.generate_category_type(x),
            )

    def sort_by(self, _field):
        for _type in self._types:
            self.diff[_type].sort_values(by=[_field])

    def calculate_diff(self):
        self.calculate_added_diff()
        self.calculate_removed_diff()
        self.calculate_full_diff()

        self.add_category_search_url()
        self.add_category_type()
        self.sort_by('wb_category_type')

    def calculate_full_diff(self):
        """
        Retrieve all different values from two dictionaries.

        Details: https://pythondata.com/quick-tip-comparing-two-pandas-dataframes-and-getting-the-differences/
        """
        df1 = pd.DataFrame(self.categories_old, columns=self._columns)
        df2 = pd.DataFrame(self.categories_new, columns=self._columns)

        df = pd.concat([df1, df2])  # concat dataframes
        df = df.reset_index(drop=True)  # reset the index
        df_gpby = df.groupby(list(df.columns))  # group by

        diff_indexes = [x[0] for x in df_gpby.groups.values() if len(x) == 1]  # reindex

        ri = df.reindex(diff_indexes)

        self.diff['full'] = ri.groupby('wb_category_url', as_index=False).first()
        self.diff_unique['full'] = self.diff['full'].groupby('wb_category_name', as_index=False).first()

        return self

    def calculate_added_diff(self):
        """
        Retrieve only new values from two dictionaries.

        :return:
        """
        df_old = pd.DataFrame(self.categories_old, columns=self._columns)
        df_new = pd.DataFrame(self.categories_new, columns=self._columns)

        df_diff = pd.merge(df_new, df_old, how='outer', indicator=True)
        self.diff['added'] = df_diff.loc[df_diff._merge == 'left_only', self._columns]
        self.diff_unique['added'] = self.diff['added'].groupby('wb_category_name', as_index=False).first()

        return self

    def calculate_removed_diff(self):
        """
        Retrieve only old values from two dictionaries.

        :return:
        """
        df_old = pd.DataFrame(self.categories_old, columns=self._columns)
        df_new = pd.DataFrame(self.categories_new, columns=self._columns)

        df_diff = pd.merge(df_old, df_new, how='outer', indicator=True)
        self.diff['removed'] = df_diff.loc[df_diff._merge == 'left_only', self._columns]
        self.diff_unique['removed'] = self.diff['removed'].groupby('wb_category_name', as_index=False).first()

        return self

    def get_categories_count(self, _type=None) -> int:
        if _type is None:
            raise Exception('type is not defined')

        return len(self.diff[_type])

    def get_categories_unique_count(self, _type=None) -> int:
        if _type is None:
            raise Exception('type is not defined')

        return len(self.diff_unique[_type])

    def dump_to_s3_file(self, _type=None):
        if _type is None:
            raise Exception('type is not defined')

        prefix = _type + '_'
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', prefix=prefix, mode='r+b', delete=True)
        temp_file_name = os.path.basename(temp_file.name)

        self.diff[_type].to_excel(temp_file.name, index=None, header=True)

        s3.upload_file(temp_file.name, env('AWS_S3_BUCKET_NAME'), temp_file_name)

        self.s3_files[_type] = temp_file_name

        return self

    def get_s3_file_name(self, _type=None):
        if _type is None:
            raise Exception('type is not defined')

        return self.s3_files[_type]


class WbCategoryStats:
    def __init__(self):
        self.data = []
        self.df = pd.DataFrame()

    def fill_from_api(self, job_id):
        sh = init_scrapinghub()

        for item in sh['client'].get_job(job_id).items.iter():
            self.data.append(item)

        self.prepare_dataframe()

        return self

    def load_from_list(self, category_data):
        self.data = category_data

        self.prepare_dataframe()

        return self

    def prepare_dataframe(self):
        self.df = pd.DataFrame(self.data)

        # если уж найдем пустые значения, то изгоним их каленым железом (вместе со всей строкой, да)
        self.df.drop(self.df[self.df['wb_price'] == ''].index, inplace=True)  # это для случая загрузки из словаря
        self.df.drop(self.df[self.df['wb_purchases_count'] == ''].index, inplace=True)  # это тоже для словаря

        # а это, если загрузили по API
        self.df.dropna(
            subset=[
                'wb_category_position',
                'wb_price',
                'wb_purchases_count',
                'wb_rating',
                'wb_reviews_count',
            ],
            inplace=True,
        )

        self.df = self.df.astype({
            'wb_category_position': int,
            'wb_price': float,
            'wb_purchases_count': int,
            'wb_rating': float,
            'wb_reviews_count': int,
        })

        self.df['wb_turnover'] = self.df['wb_price'] * self.df['wb_purchases_count']

        return self

    def get_category_name(self):
        return self.df.loc[0, 'wb_category_name'] if 'wb_category_name' in self.df.columns else 'Неизвестная категория'

    def get_category_url(self):
        return self.df.loc[0, 'wb_category_url'] if 'wb_category_url' in self.df.columns else '–'

    def get_goods_count(self):
        return len(self.df.index)

    def get_goods_price_max(self):
        return self.df['wb_price'].max()

    def get_goods_price_min(self):
        return self.df['wb_price'].min()

    def get_goods_price_mean(self):
        return round(self.df['wb_price'].mean())

    def get_sales_sum(self):
        return self.df['wb_turnover'].sum()

    def get_sales_mean(self):
        return round(self.df['wb_turnover'].mean())

    def get_sales_median(self):
        return round(self.df['wb_turnover'].median())

    def get_sales_count(self):
        return self.df['wb_purchases_count'].sum()

    def get_sales_mean_count(self):
        return round(self.df['wb_purchases_count'].mean())

    def get_sales_median_count(self):
        return round(self.df['wb_purchases_count'].median())

    def get_category_excel(self):
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', prefix='wb_category_', mode='r+b', delete=True)

        self.df.to_excel(temp_file.name, index=None, header=True)

        return temp_file
