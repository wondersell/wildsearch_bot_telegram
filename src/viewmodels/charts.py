import logging

import numpy as np

from ..helpers import (get_digits_divider, get_digits_text, smart_format_number, smart_format_prettify,
                       smart_format_round_super_hard)
from .base import BaseViewModel
from .countries import get_country_code
from .indicator import Indicator

logger = logging.getLogger(__name__)


class BarChart(BaseViewModel):
    def __init__(self, df, x_axis, y_axis, detect_countries=False):
        super().__init__()
        self._df = df
        self._x_axis = x_axis
        self._y_axis = y_axis
        self._max_value = df['val'].max()
        _, self._max_row_value = smart_format_round_super_hard(float(self._max_value))
        self._detect_countries = detect_countries

    @property
    def x_axis_name(self):
        return self._x_axis

    @property
    def y_axis_name(self):
        return self._y_axis

    @property
    def rows(self):
        rows = []

        thresholds = np.arange(0, self._max_row_value, self._max_row_value / 5)
        thresholds = np.append(thresholds, self._max_row_value)
        thresholds = np.delete(thresholds, 0)
        thresholds = thresholds[::-1]

        for threshold in thresholds:
            number, digits = smart_format_number(threshold)
            rows.append({
                'number': number,
                'digits': digits,
            })

        return rows


class IntervalBarChart(BarChart):
    @property
    def bars(self):
        bars = []

        med_interval = self._df.iloc[2].bin
        med_interval_divider = get_digits_divider(med_interval.left)
        med_interval_digits = get_digits_text(med_interval.left, skip_thousands=False)

        for row in self._df.itertuples(index=False):
            calculated_height = row[1] / self._max_row_value * 100

            # Оставляем маленькие точечки высотой 2%
            if calculated_height < 2:
                calculated_height = 2

            bars.append({
                'v': Indicator(row[1]).to_dict(),
                'height': calculated_height,
                'bin': bar_label(row[0], med_interval_divider, med_interval_digits),
            })

        return bars


class FlagsBarChart(BarChart):
    @property
    def bars(self):
        bars = []

        for row in self._df.itertuples(index=False):
            calculated_height = row[1] / self._max_row_value * 100

            # Оставляем маленькие точечки высотой 2%
            if calculated_height < 2:
                calculated_height = 2

            bars.append({
                'v': Indicator(row[1]).to_dict(),
                'height': calculated_height,
                'country_code': get_country_code(row[0]),
                'bin_text': row[0],
            })

        return bars


def bar_label(interval, divider, digits):
    if interval.left == 0:
        left = 0
    else:
        left = interval.left / divider

    if interval.right == np.inf:
        right = None
    else:
        right = interval.right / divider

    if right is not None:
        text = f'{smart_format_prettify(left)}–{smart_format_prettify(right)}'
    else:
        text = f'{smart_format_prettify(left)}+'

    return {
        'text': text,
        'digits': digits,
        'units': 'руб.',
    }
