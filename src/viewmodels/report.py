import datetime
import logging

import numpy as np
import pandas as pd
from dateutil.parser import parse as date_parse
from seller_stats.category_stats import calc_hhi, calc_sales_distribution

from .base import BaseViewModel
from .charts import BarChart
from .helpers import image_bag
from .indicator import Indicator
from .item import Item, ItemsList
from .months import months_full
from .popular_brands import PopularBrandsList
from .rating_distribution import RatingDistributionList
from .sales_distribution import SalesDistribution

logger = logging.getLogger(__name__)


class Report(BaseViewModel):
    items_field_list = [
        'id',
        'url',
        'image_urls',
        'brand_name',
        'name',
        'price',
        'purchases',
        'turnover',
        'purchases_month',
        'turnover_month',
        'first_review',
        'rating',
    ]

    def __init__(self, stats):
        self.stats = stats

    @property
    def base_current_date(self):
        today = datetime.datetime.today()
        months = months_full()

        return f'{today.day} {months[today.month]} {today.year}'

    @property
    def category_url(self):
        return self.stats.category_url()

    @property
    def category_name(self):
        return self.stats.category_name()

    @property
    def base_goods(self):
        return Indicator(number=len(self.stats.df.index), label='Товаров').to_dict()

    @property
    def base_brands(self):
        return Indicator(number=len(self.stats.df.brand_name.unique()), label='Брендов').to_dict()

    @property
    def base_turnover(self):
        return Indicator(number=self.stats.df.turnover_month.sum(), units='руб.', label='Брендов').to_dict()

    @property
    def base_sold(self):
        return Indicator(number=self.stats.df.purchases_month.sum(), units='шт.', label=None).to_dict()

    @property
    def base_turnover_median(self):
        return Indicator(number=self.stats.df.turnover_month.median(), units='руб.', label=None).to_dict()

    @property
    def base_sold_median(self):
        return Indicator(number=self.stats.df.purchases_month.median(), units='шт.', label=None).to_dict()

    @property
    def base_monopoly_index(self):
        monopoly = round(5 * calc_hhi(self.stats, by='brand_name') / 10000)  # максимум – 10 000
        return Indicator(number=monopoly, units=None, label=None).to_dict()

    @property
    def base_monopoly_index_images(self):
        return image_bag(number=self.base_monopoly_index['number_raw'], image_pale='m1', image_bright='m1a')

    @property
    def base_trash_index(self):
        trash_index = round(5 * len(self.stats.df[self.stats.df.purchases < 1].index) / len(self.stats.df.index))
        return Indicator(number=trash_index, units=None, label=None).to_dict()

    @property
    def base_trash_index_images(self):
        return image_bag(number=self.base_trash_index['number_raw'], image_pale='m2', image_bright='m2a')

    @property
    def base_first_sales(self):
        months = {
            1: 'нас.',
            2: 'нач.',
            3: 'нач.',
            4: 'нач.',
            5: 'сер.',
            6: 'сер.',
            7: 'сер.',
            8: 'сер.',
            9: 'кон.',
            10: 'кон.',
            11: 'кон.',
            12: 'кон.',
        }
        try:
            date = date_parse(self.stats.df.first_review.min())
            return f'{months[date.month]} {date.year}'
        except TypeError:
            return '–'

    @property
    def sales_distribution(self):
        # Распределение продаж
        sales_distribution_df = self.stats.df.loc[:, ['purchases', 'sku']]
        sales_distribution_df['bin'] = pd.cut(sales_distribution_df.purchases, (0, 1, 10, 100, 1000, np.inf),
                                              include_lowest=True, right=False)

        sales_distribution_df = sales_distribution_df.groupby(by='bin').sum()
        sales_distribution_df['share'] = sales_distribution_df.sku / len(self.stats.df.index)
        sales_distribution_df = sales_distribution_df.reset_index()

        logger.info('Sales distributions calculated')

        return SalesDistribution(sales_distribution_df).to_dict()

    @property
    def sales_distribution_skus_chart(self):
        distributions_price = calc_sales_distribution(self.stats)

        df = distributions_price.df.loc[:, ['bin', 'sku']]
        df['val'] = df['sku']

        return BarChart(df, x_axis='Цена', y_axis='Количество артикулов').to_dict()

    @property
    def sales_distribution_turnover_chart(self):
        distributions_price = calc_sales_distribution(self.stats)

        df = distributions_price.df.loc[:, ['bin', 'turnover_month']]
        df['val'] = df['turnover_month']

        return BarChart(df, x_axis='Цена', y_axis='Оборот').to_dict()

    @property
    def brand_countries_chart(self):
        df = self.stats.df.loc[:, ['brand_country', 'sku']].groupby(by='brand_country').sum().sort_values(by='sku', ascending=False).reset_index()
        df = df.loc[0:4, ].append(pd.DataFrame([{'brand_country': 'Другое', 'sku': df.loc[5:, ].sku.sum()}]))
        df['bin'] = df['brand_country']
        df['val'] = df['sku']
        df = df.replace('Соединенные Штаты', 'США')

        return BarChart(df, x_axis='Страна', y_axis='Количество артикулов', detect_countries=True).to_dict()

    @property
    def production_countries_chart(self):
        df = self.stats.df.loc[:, ['manufacture_country', 'sku']].groupby(by='manufacture_country').sum().sort_values(by='sku', ascending=False).reset_index()
        df = df.loc[0:4, ].append(pd.DataFrame([{'manufacture_country': 'Другое', 'sku': df.loc[5:, ].sku.sum()}]))
        df['bin'] = df['manufacture_country']
        df['val'] = df['sku']
        df = df.replace('Соединенные Штаты', 'США')

        return BarChart(df, x_axis='Страна', y_axis='Количество артикулов', detect_countries=True).to_dict()

    @property
    def popular_brands(self):
        brands_df = self.stats.df.loc[:, ['brand_name', 'sku', 'turnover_month']].groupby(by='brand_name').sum().sort_values(by='turnover_month', ascending=False).reset_index()
        brands_meta_df = self.stats.df.loc[:, ['brand_name', 'brand_url', 'brand_logo']].groupby(by='brand_name').first()
        brands_df_first_review = self.stats.df.loc[:, ['brand_name', 'first_review']].groupby(by='brand_name').min()
        brands_df_retings = self.stats.df[self.stats.df.rating != 0].loc[:, ['brand_name', 'rating']].groupby(by='brand_name').mean()

        brands_df = brands_df.merge(brands_df_first_review, on='brand_name', how='left').merge(brands_df_retings, on='brand_name', how='left').merge(brands_meta_df, on='brand_name', how='left')

        return PopularBrandsList(brands_df.head(5)).to_dict()

    @property
    def average_rating(self):
        return round(self.stats.df[self.stats.df.rating != 0].rating.mean(), 1)

    @property
    def rating_distribution(self):
        return RatingDistributionList([{'rating': threshold, 'ratio': len(self.stats.df[self.stats.df.rating == threshold]) / len(self.stats.df.index)} for threshold in [5, 4, 3, 2, 1, 0]]).to_dict()

    @property
    def best_purchases_overall(self):
        return ItemsList(self.stats.df.loc[:, self.items_field_list].sort_values(by='purchases', ascending=False).head(5)).to_dict()

    @property
    def best_sold_overall(self):
        return ItemsList(self.stats.df.loc[:, self.items_field_list].sort_values(by='turnover', ascending=False).head(5)).to_dict()

    @property
    def best_purchases_month(self):
        return ItemsList(self.stats.df.loc[:, self.items_field_list].sort_values(by='turnover_month', ascending=False).head(5)).to_dict()

    @property
    def best_sold_month(self):
        return ItemsList(self.stats.df.loc[:, self.items_field_list].sort_values(by='purchases_month', ascending=False).head(5)).to_dict()

    @property
    def goods_overview(self):
        return {
            'expensive': Item(self.stats.df.loc[:, self.items_field_list].sort_values(by='price', ascending=False).head(1).to_dict('records')[0]).to_dict(),
            'cheap': Item(self.stats.df.loc[:, self.items_field_list].sort_values(by='price', ascending=True).head(1).to_dict('records')[0]).to_dict(),
            'old': Item(self.stats.df.loc[:, self.items_field_list].sort_values(by='first_review', ascending=True).head(1).to_dict('records')[0]).to_dict(),
            'bad': Item(self.stats.df[self.stats.df.rating > 0].loc[:, self.items_field_list].sort_values(by='rating', ascending=True).head(1).to_dict('records')[0]).to_dict(),
        }
