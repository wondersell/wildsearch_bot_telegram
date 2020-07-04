from dateutil.parser import parse as date_parse

from .base import BaseListViewModel, BaseViewModel
from .indicator import Indicator


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
