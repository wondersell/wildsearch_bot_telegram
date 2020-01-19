import pytest
from src.tasks import get_cat_update_users, schedule_category_export
from src.scrapinghub_helper import *
from unittest.mock import Mock, MagicMock, patch


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
    mocked_send_message.assert_called_with(chat_id='1423', text='Вы запросили анализ каталога, он будет доступен по ссылке https://dummy.url/')


@patch('src.tasks.category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_with_exception(mocked_send_message, mocked_category_export):
    mocked_category_export.side_effect = Exception('Spider wb has more than 1 queued jobs')

    schedule_category_export('https://www.wildberries/category/url', '1423')

    mocked_category_export.assert_called()
    mocked_send_message.assert_called_with(chat_id='1423', text='Произошла ошибка при запросе каталога, попробуйте запросить его позже')
