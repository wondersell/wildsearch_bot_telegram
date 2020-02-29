from unittest.mock import patch
from freezegun import freeze_time

import pytest
import csv

from src.scrapinghub_helper import *
from src.tasks import get_cat_update_users, schedule_wb_category_export, calculate_wb_category_stats, check_requests_count_recovered, send_category_requests_count_message


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
    mocked_jobs_count.return_value = 11

    with pytest.raises(Exception) as e_info:
        wb_category_export('https://www.wildberries.ru/category/dummy', 123)

    assert str(e_info.value) == 'Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs'


def test_get_cat_update_users(bot_user):
    bot_user.subscribe_to_wb_categories_updates = True
    bot_user.save()

    users = get_cat_update_users()

    assert len(users) == 1
    assert users[0] == bot_user.chat_id


@patch('scrapinghub.client.jobs.Jobs.count')
@patch('scrapinghub.client.jobs.Jobs.run')
def test_category_export_correct(mocked_jobs_run, mocked_jobs_count):
    mocked_jobs_count.return_value = 0
    mocked_jobs_run.return_value.key = '1423'

    result_url = wb_category_export('https://www.wildberries.ru/category/dummy', 123)

    assert result_url == 'https://app.scrapinghub.com/p/1423'


@patch('src.tasks.check_requests_count_recovered.apply_async')
@patch('src.tasks.wb_category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_correct(mocked_send_message, mocked_category_export, mocked_check_requests_count_recovered):
    mocked_category_export.return_value='https://dummy.url/'

    schedule_wb_category_export('https://www.wildberries/category/url', '1423')

    mocked_category_export.assert_called()
    assert 'Мы обрабатываем ваш запрос' in mocked_send_message.call_args.kwargs['text']
    mocked_check_requests_count_recovered.assert_called()


@patch('src.tasks.wb_category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_with_exception(mocked_send_message, mocked_category_export):
    mocked_category_export.side_effect = Exception('Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs')

    schedule_wb_category_export('https://www.wildberries/category/url', '1423')

    mocked_category_export.assert_called()
    assert 'мы сейчас не можем обработать ваш запрос' in mocked_send_message.call_args.kwargs['text']


@patch('src.tasks.send_category_requests_count_message.delay')
@patch('telegram.Bot.send_document')
@patch('telegram.Bot.send_message')
def test_category_export_task_sends_message(mocked_send_message, mocked_send_document, mocked_send_category_requests_count_message):
    calculate_wb_category_stats('414324/1/356', '1423')

    mocked_send_message.assert_called()
    mocked_send_document.assert_called()
    mocked_send_category_requests_count_message.assert_called()


def test_category_stats_load_from_list(stats, sample_category_correct):
    stats.load_from_list(sample_category_correct)

    assert isinstance(stats.df, pd.DataFrame)
    assert len(stats.df.index) == 255


@pytest.mark.parametrize('method_name, expected_value', [
    ['get_goods_count', 255],
    ['get_goods_price_max', 5213],
    ['get_goods_price_mean', 760],
    ['get_sales_mean', 18069],
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
    ['get_sales_mean', 5],
    ['get_sales_median', 4],
    ['get_sales_sum', 14],
    ['get_sales_mean_count', 2],
    ['get_sales_median_count', 2],
    ['get_sales_count', 6],
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


@patch('telegram.Bot.send_message')
def _test_check_requests_count_recovered_fully(mocked_send_message, bot_user, create_telegram_command_logs):
    bot_user.save()

    with freeze_time("2030-06-15 01:20:00"):
        create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time("2030-06-16 01:21:00"):
        check_requests_count_recovered(bot_user.chat_id)
        assert 'Рок-н-ролл' in mocked_send_message.call_args.kwargs['text']


@patch('telegram.Bot.send_message')
def test_check_requests_count_recovered_not_fully(mocked_send_message, bot_user, create_telegram_command_logs):
    bot_user.save()

    with freeze_time("2030-06-15 01:20:00"):
        create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time("2030-06-16 01:19:00"):
        check_requests_count_recovered(bot_user.chat_id)

        mocked_send_message.assert_not_called()


@patch('telegram.Bot.send_message')
def test_send_category_requests_count_message(mocked_send_message, bot_user, create_telegram_command_logs):
    bot_user.daily_catalog_requests_limit = 5
    bot_user.save()

    create_telegram_command_logs(4, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    send_category_requests_count_message(bot_user.chat_id)

    assert 'Вам доступно' in mocked_send_message.call_args.kwargs['text']
    assert '🌕🌑🌑🌑🌑' in mocked_send_message.call_args.kwargs['text']
