from unittest.mock import patch

import pytest
import csv
import os

from src.scrapinghub_helper import *
from src.tasks import get_cat_update_users, schedule_category_export, calculate_category_stats


@pytest.fixture()
def stats():
    return WbCategoryStats()


@pytest.fixture()
def sample_category_correct():
    f = open('tests/mocks/sample_wb_category_correct.csv')
    return csv.DictReader(f)


@pytest.fixture()
def sample_category_missing():
    f = open('tests/mocks/sample_wb_category_with_missing.csv')
    return csv.DictReader(f)


@pytest.fixture()
def sample_category_with_names():
    f = open('tests/mocks/sample_wb_category_with_names.csv')
    return csv.DictReader(f)


@patch('scrapinghub.client.jobs.Jobs.count')
def test_scheduled_jobs_count(mocked_jobs_count):
    mocked_jobs_count.return_value = 5

    cnt = scheduled_jobs_count(init_scrapinghub(), 'wb')

    assert cnt == 10


@patch('scrapinghub.client.jobs.Jobs.count')
def test_category_export_too_many_jobs_exception(mocked_jobs_count):
    mocked_jobs_count.return_value = 5

    with pytest.raises(Exception) as e_info:
        category_export('https://www.wildberries.ru/category/dummy', 123)

    assert str(e_info.value) == 'Spider wb has more than 1 queued jobs'


def test_get_cat_update_users(monkeypatch):
    monkeypatch.setenv('WILDSEARCH_TEST_USER_LIST', '1234,4321')

    users = get_cat_update_users()

    assert '1234' in users
    assert '4321' in users


@patch('scrapinghub.client.jobs.Jobs.count')
@patch('scrapinghub.client.jobs.Jobs.run')
def test_category_export_correct(mocked_jobs_run, mocked_jobs_count):
    mocked_jobs_count.return_value = 0
    mocked_jobs_run.return_value.key = '1423'

    result_url = category_export('https://www.wildberries.ru/category/dummy', 123)

    assert result_url == 'https://app.scrapinghub.com/p/1423'


@patch('src.tasks.category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_correct(mocked_send_message, mocked_category_export):
    mocked_category_export.return_value='https://dummy.url/'

    schedule_category_export('https://www.wildberries/category/url', '1423')

    mocked_category_export.assert_called()
    mocked_send_message.assert_called_with(chat_id='1423', text='Я поставил каталог в очередь на исследование. Скоро пришлю результаты.')


@patch('src.tasks.category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_with_exception(mocked_send_message, mocked_category_export):
    mocked_category_export.side_effect = Exception('Spider wb has more than 1 queued jobs')

    schedule_category_export('https://www.wildberries/category/url', '1423')

    mocked_category_export.assert_called()
    mocked_send_message.assert_called_with(chat_id='1423', text='Произошла ошибка при запросе каталога, попробуйте запросить его позже')


@patch('telegram.Bot.send_document')
@patch('telegram.Bot.send_message')
def test_category_export_task_sends_message(mocked_send_message, mocked_send_document):
    calculate_category_stats('414324/1/356', '1423')

    mocked_send_message.assert_called()
    mocked_send_document.assert_called()


def test_category_stats_load_from_list(stats, sample_category_correct):
    stats.load_from_list(sample_category_correct)

    assert isinstance(stats.df, pd.DataFrame)
    assert len(stats.df.index) == 255


@pytest.mark.parametrize('method_name, expected_value', [
    ['get_goods_count', 255],
    ['get_goods_price_max', 5213],
    ['get_goods_price_mean', 760.09],
    ['get_sales_mean', 18068.67],
    ['get_sales_median', 3250],
    ['get_sales_sum', 4607512],
])
def test_category_stats_basic_stats_correct(stats, sample_category_correct, method_name, expected_value):
    stats.load_from_list(sample_category_correct)

    assert getattr(stats, method_name)() == expected_value


@pytest.mark.parametrize('method_name, expected_value', [
    ['get_goods_count', 3],
    ['get_goods_price_max', 3],
    ['get_goods_price_mean', 2],
    ['get_sales_mean', 4.67],
    ['get_sales_median', 4],
    ['get_sales_sum', 14],
])
def test_category_stats_basic_stats_missing(stats, sample_category_missing, method_name, expected_value):
    stats.load_from_list(sample_category_missing)

    assert getattr(stats, method_name)() == expected_value


def test_category_stats_get_category_name(stats, sample_category_with_names):
    stats.load_from_list(sample_category_with_names)

    assert stats.get_category_name() == 'Ювелирные иконы'


def test_category_stats_get_category_url(stats, sample_category_with_names):
    stats.load_from_list(sample_category_with_names)

    assert stats.get_category_url() == 'https://www.wildberries.ru/catalog/yuvelirnye-ukrasheniya/ikony'


def test_category_stats_get_file(stats, sample_category_with_names):
    stats.load_from_list(sample_category_with_names)

    export_file = stats.get_category_excel()

    assert os.path.isfile(export_file.name)
