import numpy as np
from seller_stats.utils.formatters import format_percent

from .base import BaseListViewModel, BaseViewModel


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
