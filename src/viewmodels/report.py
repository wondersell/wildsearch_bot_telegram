import datetime
import inspect
import logging

import numpy as np
import pandas as pd
from dateutil.parser import parse as date_parse
from seller_stats.category_stats import calc_hhi
from seller_stats.utils.formatters import format_percent

from ..helpers import smart_format_number

logger = logging.getLogger(__name__)


class BaseViewModel(object):
    def to_dict(self):
        return dict(inspect.getmembers(self))


class BaseListViewModel(object):
    def __init__(self):
        self.items = []

    def to_dict(self):
        return [item.to_dict() for item in self.items]


class Indicator(BaseViewModel):
    def __init__(self, number, units=None, label=None, precise=False):
        self._number_raw = number
        self._units = units
        self._label = label
        self._precise = precise

        if precise is False:
            self._number, self._text_digits = smart_format_number(number)
        else:
            self._number, self._text_digits = number, ''

    @property
    def number_raw(self):
        return self._number_raw

    @property
    def number(self):
        return self._number

    @property
    def digits(self):
        return self._text_digits

    @property
    def units(self):
        return self._units

    @property
    def label(self):
        return self._label


class SalesDistributionItem(BaseViewModel):
    def __init__(self, item):
        self._interval = item['bin']
        self._share = item['share']

    @property
    def label(self):
        # 0 продаж
        # 1 - 10 продаж
        # > 10 продаж
        if self._interval.left == 0:
            return '0'

        if self._interval.right == np.inf:
            return f'> {int(self._interval.left)}'

        return f'{int(self._interval.left)}-{int(self._interval.right)}'

    @property
    def ratio(self):
        return format_percent(round(self._share, 2))


class SalesDistribution(BaseListViewModel):
    def __init__(self, df):
        super().__init__()
        for item in df.to_dict('records'):
            self.items.append(SalesDistributionItem(item))


class PopularBrandsItem(BaseViewModel):
    def __init__(self, item):
        self._url = item['brand_url']
        self._logo = item['brand_logo']
        self._name = item['brand_name']
        self._goods = item['sku']
        self._turnover = item['turnover_month']
        self._first_review = item['first_review']
        self._average_rating = item['rating']

    @property
    def url(self):
        return self._url

    @property
    def name(self):
        return self._name

    @property
    def logo(self):
        return self._logo.replace('//', 'http://')

    @property
    def goods(self):
        return Indicator(number=self._goods, units='шт.')

    @property
    def turnover(self):
        return Indicator(number=self._turnover, units='руб.')

    @property
    def first_review_date(self):
        months = {
            1: 'янв.',
            2: 'фев.',
            3: 'мар.',
            4: 'апр.',
            5: 'май.',
            6: 'июн.',
            7: 'июл.',
            8: 'авг.',
            9: 'сен.',
            10: 'окт.',
            11: 'ноя.',
            12: 'дек.',
        }
        try:
            date = date_parse(self._first_review)
            return f'{months[date.month]} {date.year}'
        except TypeError:
            return '–'

    @property
    def average_rating(self):
        return round(self._average_rating, 1)


class PopularBrandsList(BaseListViewModel):
    def __init__(self, df):
        super().__init__()
        for item in df.to_dict('records'):
            self.items.append(PopularBrandsItem(item))


class RatingDistributionItem(BaseViewModel):
    def __init__(self, item):
        self._rating = item['rating']
        self._ratio = item['ratio']

    @property
    def label(self):
        if self._rating == 0:
            return 'Без рейтинга'

        return self._rating

    @property
    def ratio(self):
        return format_percent(round(self._ratio, 2))

    @property
    def images(self):
        return image_bag(number=self._rating, image_pale='star3', image_bright='star2') if self._rating > 0 else []


class RatingDistributionList(BaseListViewModel):
    def __init__(self, distributions):
        super().__init__()
        for item in distributions:
            self.items.append(RatingDistributionItem(item))


class Item(BaseViewModel):
    def __init__(self, item):
        self._id = item['id']
        self._url = item['url']
        self._brand_name = item['brand_name']
        self._name = item['name']
        self._price = item['price']
        self._purchases = item['purchases']
        self._turnover = item['turnover']
        self._purchases_month = item['purchases_month']
        self._turnover_month = item['turnover_month']
        self._first_review = item['first_review']
        self._rating = item['rating']
        self._images = item['image_urls']

    @property
    def url(self):
        return self._url

    @property
    def logo(self):
        return self._images[0].replace('//', 'http://')

    @property
    def name(self):
        return f'{self._brand_name} / {self._name}'

    @property
    def price(self):
        return Indicator(number=self._price, units='руб.', precise=True)

    @property
    def purchases(self):
        return Indicator(number=self._purchases, units='шт.')

    @property
    def turnover(self):
        return Indicator(number=self._turnover, units='руб.')

    @property
    def purchases_month(self):
        return Indicator(number=self._purchases_month, units='шт.')

    @property
    def turnover_month(self):
        return Indicator(number=self._turnover_month, units='руб.')

    @property
    def first_review_date(self):
        months = {
            1: 'янв.',
            2: 'фев.',
            3: 'мар.',
            4: 'апр.',
            5: 'май.',
            6: 'июн.',
            7: 'июл.',
            8: 'авг.',
            9: 'сен.',
            10: 'окт.',
            11: 'ноя.',
            12: 'дек.',
        }
        try:
            date = date_parse(self._first_review)
            return f'{months[date.month]} {date.year}'
        except TypeError:
            return '–'

    @property
    def average_rating(self):
        return round(self._rating, 1)


class ItemsList(BaseListViewModel):
    def __init__(self, df):
        super().__init__()
        for item in df.to_dict('records'):
            self.items.append(Item(item))

'''
	bin	        sku	    turnover_month	    purchases_month
0	0-250	    836	    4532545.77	        21861.17
1	250-500	    5173	27703352.05	        74919.29
2	500-750	    3410	20352363.91	        34097.00
3	750-1000	1808	12764585.67	        15119.54
4	1000-1250	807	    4339296.15	        3954.55
5	>1250	    1450	4796004.02	        2849.81
'''

'''
bin         value
0-250       4532545.77
250-500     27703352.05
500-750     20352363.91
750-1000    12764585.67
1000-1250   4339296.15
>1250       4796004.02
'''
class BarChart(BaseViewModel):
    def __init__(self, df, x_axis, y_axis):
        super().__init__()
        self._df = df
        self._x_axis = x_axis
        self._y_axis = y_axis

    @property
    def x_axis_name(self):
        return self._x_axis

    @property
    def y_axis_name(self):
        return self._y_axis

    @property
    def bars(self):
        return []

    @property
    def rows(self):
        return []

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
        return datetime.datetime.today().strftime('%d %B %Y')

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
        return None

    @property
    def sales_distribution_turnover_chart(self):
        return None

    @property
    def brand_countries_chart(self):
        return None

    @property
    def production_countries_chart(self):
        return None

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


def image_bag(number, image_pale, image_bright, maximum=5):
    images = []

    full_images = int(number)
    empty_images = maximum - full_images  # У нас пятибальная шкала

    for i in range(1, full_images + 1):
        images.append(image_bright)

    for i in range(1, empty_images + 1):
        images.append(image_pale)

    return images
