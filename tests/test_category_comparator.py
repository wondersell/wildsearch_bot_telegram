import os

import pytest
from faker import Faker

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


@pytest.mark.parametrize('lists, diff_count', [
    [make_categories(1, 2, 1), 1],  # когда есть одна новая категория
    [make_categories(1, 2, 2), 2],  # когда все категории новые
    [make_categories(10, 10, 0), 0],  # когда все категории старые
    [make_categories(10, 5, 5), 5],  # когда категорий меньше и все новые
    [make_categories(10, 5, 0), 0],  # когда категорий меньше и все старые
    [make_categories(10, 15, 8), 8]  # когда категорий больше и частично новые
])
def test_compare_two_lists_added_categories_count(comparator, lists, diff_count):
    comparator.load_from_list(lists[0], lists[1])
    comparator.calculate_added_diff()

    assert comparator.get_categories_count() is diff_count


@pytest.mark.parametrize('lists, diff_count', [
    [make_categories(1, 2, 1), 0],  # когда есть одна новая категория
    [make_categories(1, 2, 2), 1],  # когда все категории новые
    [make_categories(10, 10, 0), 0],  # когда все категории старые
    [make_categories(10, 5, 5), 10],  # когда категорий меньше и все новые
    [make_categories(10, 5, 0), 5],  # когда категорий меньше и все старые
    [make_categories(10, 15, 8), 3]  # когда категорий больше и частично новые
])
def test_compare_two_lists_removed_categories_count(comparator, lists, diff_count):
    comparator.load_from_list(lists[0], lists[1])
    comparator.calculate_removed_diff()

    assert comparator.get_categories_count() is diff_count


@pytest.mark.parametrize('lists, diff_count', [
    [make_categories(1, 2, 1), 1],  # когда есть одна новая категория
    [make_categories(1, 2, 2), 3],  # когда все категории новые
    [make_categories(10, 10, 0), 0],  # когда все категории старые
    [make_categories(10, 5, 5), 15],  # когда категорий меньше и все новые
    [make_categories(10, 5, 0), 5],  # когда категорий меньше и все старые
    [make_categories(10, 15, 8), 11]  # когда категорий больше и частично новые
])
def test_compare_two_lists_full_diff_categories_count(comparator, lists, diff_count):
    comparator.load_from_list(lists[0], lists[1])
    comparator.calculate_full_diff()

    assert comparator.get_categories_count() is diff_count


def test_all_fields_present(comparator_random):
    comparator_random.calculate_full_diff()

    assert list(comparator_random.diff.columns) == ['wb_category_url', 'wb_category_name']


def test_export_file_dump_full_double(comparator_random):
    comparator_random.calculate_full_diff()
    comparator_random.dump_to_tempfile()

    assert os.path.getsize(comparator_random.get_from_tempfile().name) > 0
    assert os.path.getsize(comparator_random.get_from_tempfile().name) > 0


def test_export_file_prefix(comparator_random):
    comparator_random.calculate_full_diff()
    comparator_random.dump_to_tempfile(prefix='prefixed_')

    assert 'prefixed_' in comparator_random.get_from_tempfile().name