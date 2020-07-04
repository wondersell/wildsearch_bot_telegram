from dateutil.parser import parse as date_parse

from .base import BaseListViewModel, BaseViewModel
from .indicator import Indicator


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
