import re
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from freezegun import freeze_time

from src.helpers import category_export, init_scrapinghub, scheduled_jobs_count
from src.models import log_command
from src.tasks import (calculate_category_stats, check_requests_count_recovered, get_cat_update_users,
                       schedule_category_export, send_category_requests_count_message)


@pytest.fixture()
def sample_category_data_raw(current_path):
    def _sample_category_data_raw(spider='wb'):
        return open(current_path + f'/mocks/scrapinghub_items_{spider}_raw.msgpack', 'rb').read()

    return _sample_category_data_raw


@pytest.fixture()
def set_scrapinghub_requests_mock(requests_mock, sample_category_data_raw):
    def _set_scrapinghub_requests_mock(pending_count=1, running_count=1, job_id='123/1/2'):
        spider = 'wb' if re.findall(r'\d+\/(\d+)\/\d+', job_id)[0] == str(1) else 'ozon'

        requests_mock.get('https://storage.scrapinghub.com/ids/414324/spider/wb', text='1')
        requests_mock.get('https://storage.scrapinghub.com/ids/414324/spider/ozon', text='1')
        requests_mock.get('https://storage.scrapinghub.com/jobq/414324/count?state=pending&spider=wb', text=f'{pending_count}')
        requests_mock.get('https://storage.scrapinghub.com/jobq/414324/count?state=running&spider=wb', text=f'{running_count}')
        requests_mock.post('https://app.scrapinghub.com/api/run.json', json={'status': 'ok', 'jobid': f'{job_id}'})
        requests_mock.get(f'https://storage.scrapinghub.com/items/{job_id}?meta=_key', content=sample_category_data_raw(spider=spider), headers={'Content-Type': 'application/x-msgpack; charset=UTF-8'})
        requests_mock.get(f'https://storage.scrapinghub.com/jobs/{job_id}/state', text='"finished"')

    return _set_scrapinghub_requests_mock


def test_scheduled_jobs_count(set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(pending_count=2, running_count=3)
    client, project = init_scrapinghub()

    cnt = scheduled_jobs_count(project, 'wb')

    assert cnt == 5


def test_category_export_too_many_jobs_exception(set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(pending_count=2, running_count=10)

    with pytest.raises(Exception) as e_info:
        category_export('https://www.wildberries.ru/category/dummy', 123)

    assert str(e_info.value) == 'Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs'


def test_get_cat_update_users(bot_user):
    bot_user.subscribe_to_wb_categories_updates = True
    bot_user.save()

    users = get_cat_update_users()

    assert len(users) == 1
    assert users[0] == bot_user.chat_id


def test_category_export_correct(set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(job_id='123/1/1234')

    result_url = category_export('https://www.wildberries.ru/category/dummy', 321)

    assert result_url == 'https://app.scrapinghub.com/p/123/1/1234'


@patch('src.tasks.check_requests_count_recovered.apply_async')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_correct(mocked_send_message, mocked_check_requests_count_recovered, bot_user, set_scrapinghub_requests_mock):
    set_scrapinghub_requests_mock(job_id='123/1/1234')

    log_item = log_command(bot_user, 'wb_catalog', 'la-la-la')

    schedule_category_export('https://www.wildberries/category/url', bot_user.chat_id, log_item.id)

    assert 'Мы обрабатываем ваш запрос' in mocked_send_message.call_args.kwargs['text']
    mocked_check_requests_count_recovered.assert_called()


@patch('src.tasks.category_export')
@patch('telegram.Bot.send_message')
def test_schedule_category_export_with_exception(mocked_send_message, mocked_category_export, bot_user):
    mocked_category_export.side_effect = Exception('Spider wb has more than SCHEDULED_JOBS_THRESHOLD queued jobs')
    log_item = log_command(bot_user, 'wb_catalog', 'la-la-la')

    schedule_category_export('https://www.wildberries/category/url', bot_user.chat_id, log_item.id)

    mocked_category_export.assert_called()
    assert 'мы сейчас не можем обработать ваш запрос' in mocked_send_message.call_args.kwargs['text']


@patch('src.tasks.send_category_requests_count_message.delay')
@patch('telegram.Bot.send_document')
@patch('telegram.Bot.send_message')
def test_category_export_task_sends_message(mocked_send_message, mocked_send_document, mocked_send_category_requests_count_message, set_scrapinghub_requests_mock, bot_user):
    set_scrapinghub_requests_mock(job_id='414324/1/926')

    calculate_category_stats('414324/1/926', bot_user.chat_id)

    required_stats = [
        'Количество товаров',
        'Продаж всего',
        'В среднем продаются по',
        'Медиана продаж',
    ]

    for message in required_stats:
        assert message in mocked_send_message.call_args.kwargs['text']

    mocked_send_message.assert_called()
    mocked_send_document.assert_called()
    mocked_send_category_requests_count_message.assert_called()


@patch('telegram.Bot.send_message')
def test_category_export_task_not_finished(mocked_send_message, set_scrapinghub_requests_mock, bot_user, requests_mock):
    requests_mock.get('https://storage.scrapinghub.com/jobs/414324/1/926/state', text='"running"')

    with pytest.raises(Retry):
        calculate_category_stats('414324/1/926', bot_user.chat_id)
        mocked_send_message.assert_not_called()


@patch('telegram.Bot.send_message')
def test_category_export_task_empty_category(mocked_send_message, set_scrapinghub_requests_mock, bot_user, current_path, requests_mock):
    set_scrapinghub_requests_mock(job_id='414324/1/926')
    requests_mock.get('https://storage.scrapinghub.com/items/414324/1/926?meta=_key', content=open(current_path + '/mocks/scrapinghub_items_wb_empty.msgpack', 'rb').read(), headers={'Content-Type': 'application/x-msgpack; charset=UTF-8'})

    calculate_category_stats('414324/1/926', bot_user.chat_id)

    mocked_send_message.assert_called()
    assert 'Мы не смогли обработать ссылку' in mocked_send_message.call_args.kwargs['text']


@pytest.mark.parametrize('job_id, expected_marketplace', [
    ['414324/1/926', 'Wildberries'],
])
@patch('telegram.Bot.send_document')
@patch('telegram.Bot.send_message')
def test_category_export_task_sends_correct_filenames(mocked_send_message, mocked_send_document, job_id, expected_marketplace, set_scrapinghub_requests_mock, bot_user):
    set_scrapinghub_requests_mock(job_id=job_id)

    calculate_category_stats(job_id, bot_user.chat_id)

    assert expected_marketplace in mocked_send_document.call_args.kwargs['filename']


@patch('telegram.Bot.send_message')
def test_check_requests_count_recovered_fully(mocked_send_message, bot_user, create_telegram_command_logs):
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
