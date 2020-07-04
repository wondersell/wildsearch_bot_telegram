from seller_stats.utils.formatters import format_percent

from .base import BaseListViewModel, BaseViewModel
from .helpers import image_bag


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
