import csv
import os
from unittest.mock import patch

import pandas as pd
import pytest
from freezegun import freeze_time

from src.models import log_command
from src.scrapinghub_helper import init_scrapinghub, scheduled_jobs_count, wb_category_export
from src.tasks import (calculate_wb_category_stats, check_requests_count_recovered, get_cat_update_users,
                       schedule_wb_category_export, send_category_requests_count_message)


@pytest.fixture()
def sample_category_data(current_path):
    def _sample_category_data(mock='sample_category_transformed', fieldnames=None):
        return [row for row in csv.DictReader(open(current_path + f'/mocks/{mock}.csv'), fieldnames=fieldnames)]

    return _sample_category_data


@pytest.fixture()
def sample_category_data_raw(current_path):
    with open(current_path + f'/mocks/scrapinghub_items_raw.txt', 'r') as file:
        data = file.read()

    return data


@pytest.fixture()
def sample_category_correct():
    mock_file = open('tests/mocks/sample_wb_category_correct.csv')
    return csv.DictReader(mock_file)


@pytest.fixture()
def sample_category_missing():
    mock_file = open('tests/mocks/sample_wb_category_with_missing.csv')
    return csv.DictReader(mock_file)


@pytest.fixture()
def sample_category_with_names():
    mock_file = open('tests/mocks/sample_wb_category_with_names.csv')
    return csv.DictReader(mock_file)


@pytest.fixture()
def set_scrapinghub_requests_mock(requests_mock, scrapinghub_api_response, sample_category_data_raw):
    def _set_scrapinghub_requests_mock(pending_count=1, running_count=1, job_id='123/1/2'):
        requests_mock.get('https://storage.scrapinghub.com/ids/414324/spider/wb', text='1')
        requests_mock.get('https://storage.scrapinghub.com/jobq/414324/count?state=pending&spider=wb', text=f'{pending_count}')
        requests_mock.get('https://storage.scrapinghub.com/jobq/414324/count?state=running&spider=wb', text=f'{running_count}')
        requests_mock.post('https://app.scrapinghub.com/api/run.json', json={'status': 'ok', 'jobid': f'{job_id}'})
        requests_mock.get(f'https://storage.scrapinghub.com/items/{job_id}?meta=_key', text=sample_category_data_raw)

    return _set_scrapinghub_requests_mock


def test_scheduled_jobs_count(set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(pending_count=2, running_count=3)
    client, project = init_scrapinghub()

    cnt = scheduled_jobs_count(project, 'wb')

    assert cnt == 5


def test_category_export_too_many_jobs_exception(set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(pending_count=2, running_count=10)

    with pytest.raises(Exception) as e_info:
        wb_category_export('https://www.wildberries.ru/category/dummy', 123)

    assert str(e_info.value) == 'Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs'


def test_get_cat_update_users(bot_user):
    bot_user.subscribe_to_wb_categories_updates = True
    bot_user.save()

    users = get_cat_update_users()

    assert len(users) == 1
    assert users[0] == bot_user.chat_id


def test_category_export_correct(set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(job_id='123/1/1234')

    result_url = wb_category_export('https://www.wildberries.ru/category/dummy', 321)

    assert result_url == 'https://app.scrapinghub.com/p/123/1/1234'


@patch('src.tasks.check_requests_count_recovered.apply_async')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_correct(mocked_send_message, mocked_check_requests_count_recovered, bot_user, set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(job_id='123/1/1234')

    log_item = log_command(bot_user, 'wb_catalog', 'la-la-la')

    schedule_wb_category_export('https://www.wildberries/category/url', bot_user.chat_id, log_item.id)

    assert 'Мы обрабатываем ваш запрос' in mocked_send_message.call_args.kwargs['text']
    mocked_check_requests_count_recovered.assert_called()


@patch('src.tasks.wb_category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_with_exception(mocked_send_message, mocked_category_export, bot_user):
    mocked_category_export.side_effect = Exception('Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs')
    log_item = log_command(bot_user, 'wb_catalog', 'la-la-la')

    schedule_wb_category_export('https://www.wildberries/category/url', bot_user.chat_id, log_item.id)

    mocked_category_export.assert_called()
    assert 'мы сейчас не можем обработать ваш запрос' in mocked_send_message.call_args.kwargs['text']


@patch('src.tasks.send_category_requests_count_message.delay')
@patch('telegram.Bot.send_document')
@patch('telegram.Bot.send_message')
def _test_category_export_task_sends_message(mocked_send_message, mocked_send_document, mocked_send_category_requests_count_message, set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(job_id='414324/1/735')

    calculate_wb_category_stats('414324/1/735', '1423')

    mocked_send_message.assert_called()
    mocked_send_document.assert_called()
    mocked_send_category_requests_count_message.assert_called()


@patch('telegram.Bot.send_message')
def _test_check_requests_count_recovered_fully(mocked_send_message, bot_user, create_telegram_command_logs):
    bot_user.save()

    with freeze_time('2030-06-15 01:20:00'):
        create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-16 01:21:00'):
        check_requests_count_recovered(bot_user.chat_id)
        assert 'Рок-н-ролл' in mocked_send_message.call_args.kwargs['text']


@patch('telegram.Bot.send_message')
def test_check_requests_count_recovered_not_fully(mocked_send_message, bot_user, create_telegram_command_logs):
    bot_user.save()

    with freeze_time('2030-06-15 01:20:00'):
        create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-16 01:19:00'):
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
