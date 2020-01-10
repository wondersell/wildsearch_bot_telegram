import os

import pytest
from faker import Faker
import pandas as pd

from src.scrapinghub_helper import *

fake = Faker()
fake.seed(0)


def make_categories(len_1, len_2, diff_count):
    lists = [[], []]

    # заполняем первый лист (старые категории)
    for i in range(len_1):
        lists[0].append({
            'wb_category_name': fake.company(),
            'wb_category_url': fake.url()
        })

    # заполняем второй лист категориями, которые должны совпадать
    for i in range(len_2 - diff_count):
        lists[1].append(lists[0][i])

    # добиваем второй лист категориями, которые должны отличаться
    for i in range(len_2 - len(lists[1])):
        lists[1].append({
            'wb_category_name': fake.company(),
            'wb_category_url': fake.url()
        })

    return lists


@pytest.fixture()
def comparator():
    return WbCategoryComparator()


@pytest.fixture()
def comparator_random():
    comparator = WbCategoryComparator()
    lists = make_categories(10, 20, 15)
    comparator.load_from_list(lists[0], lists[1])
    return comparator


def test_load_from_lists(comparator):
    lists = make_categories(1, 2, 1)

    comparator.load_from_list(lists[0], lists[1])

    assert comparator.categories_old is lists[0]
    assert comparator.categories_new is lists[1]


@pytest.mark.parametrize('lists, diff_added_count, diff_removed_count, diff_full_count', [
    [make_categories(1, 2, 1),      1, 0, 1],  # когда есть одна новая категория
    [make_categories(1, 2, 2),      2, 1, 3],  # когда все категории новые
    [make_categories(10, 10, 0),    0, 0, 0],  # когда все категории старые
    [make_categories(10, 5, 5),     5, 10, 15],  # когда категорий меньше и все новые
    [make_categories(10, 5, 0),     0, 5, 5],  # когда категорий меньше и все старые
    [make_categories(10, 15, 8),    8, 3, 11]  # когда категорий больше и частично новые
])
def test_compare_two_lists_added_categories_count(comparator, lists, diff_added_count, diff_removed_count, diff_full_count):
    comparator.load_from_list(lists[0], lists[1])
    comparator.calculate_diff()

    assert comparator.get_categories_count('added') is diff_added_count
    assert comparator.get_categories_count('removed') is diff_removed_count
    assert comparator.get_categories_count('full') is diff_full_count


def test_get_category_count_raises_exception(comparator_random):
    comparator_random.calculate_diff()
    with pytest.raises(Exception) as execinfo:
        comparator_random.get_categories_count()

    assert 'type is not defined' in str(execinfo.value)


def test_all_fields_present(comparator_random):
    expected_columns = WbCategoryComparator._columns.sort()
    comparator_random.calculate_diff()

    assert list(comparator_random.diff['added'].columns).sort() == expected_columns
    assert list(comparator_random.diff['removed'].columns).sort() == expected_columns
    assert list(comparator_random.diff['full'].columns).sort() == expected_columns


@pytest.mark.parametrize('_type', ['added', 'removed', 'full'])
def test_export_file_dump_full_double(comparator_random, _type):
    comparator_random.calculate_diff()
    comparator_random.dump_to_tempfile(_type=_type)

    assert os.path.getsize(comparator_random.get_from_tempfile(_type=_type).name) > 0
    assert os.path.getsize(comparator_random.get_from_tempfile(_type=_type).name) > 0


@pytest.mark.parametrize('_type, expected_prefix', [
    ['added', 'added_'],
    ['removed', 'removed_'],
    ['full', 'full_']
])
def test_export_file_prefix(comparator_random, _type, expected_prefix):
    comparator_random.calculate_diff()
    comparator_random.dump_to_tempfile(_type=_type)

    assert expected_prefix in comparator_random.get_from_tempfile(_type=_type).name


@pytest.mark.parametrize('_type', [None, pd.DataFrame()])
def test_fill_types_with(_type):
    comparator = WbCategoryComparator()
    filled = comparator.fill_types_with(_type)

    assert filled['added'] is _type
    assert filled['removed'] is _type
    assert filled['full'] is _type


@pytest.mark.parametrize('category_name, expected_url', [
    ['Спортивная обувь', 'https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%A1%D0%BF%D0%BE%D1%80%D1%82%D0%B8%D0%B2%D0%BD%D0%B0%D1%8F%20%D0%BE%D0%B1%D1%83%D0%B2%D1%8C'],
    ['Распродажа обуви: -25% промокод', 'https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%A0%D0%B0%D1%81%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D0%B6%D0%B0%20%D0%BE%D0%B1%D1%83%D0%B2%D0%B8%3A%20-25%25%20%D0%BF%D1%80%D0%BE%D0%BC%D0%BE%D0%BA%D0%BE%D0%B4'],
    ['Blu-Ray проигрыватели', 'https://www.wildberries.ru/catalog/0/search.aspx?search=Blu-Ray%20%D0%BF%D1%80%D0%BE%D0%B8%D0%B3%D1%80%D1%8B%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D0%B8'],
    ['Рюкзаки, сумки, чехлы', 'https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%A0%D1%8E%D0%BA%D0%B7%D0%B0%D0%BA%D0%B8%2C%20%D1%81%D1%83%D0%BC%D0%BA%D0%B8%2C%20%D1%87%D0%B5%D1%85%D0%BB%D1%8B']
])
def test_search_url_field_generator(category_name, expected_url):
    comparator = WbCategoryComparator()
    generated_url = comparator.generate_search_url(category_name)

    assert generated_url == expected_url


@pytest.mark.parametrize('_type', ['added', 'removed', 'full'])
def test_search_url_field_present(comparator_random, _type):
    comparator_random.calculate_diff()

    assert 'wb_category_search_url' in comparator_random.diff[_type].columns
    assert 'www.wildberries.ru' in comparator_random.diff[_type].iloc[0].at['wb_category_search_url']
