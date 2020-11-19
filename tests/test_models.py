from datetime import datetime

import pytest
from freezegun import freeze_time

from src.models import (LogCommandItem, User, get_subscribed_to_wb_categories_updates, log_command,
                        user_get_by_chat_id, user_get_by_update)


def test_user_get_by_chat_id():
    u_created = User.create(chat_id=1234)

    u_fetched = user_get_by_chat_id(chat_id=1234)

    assert u_created == u_fetched


@freeze_time('2030-01-15')
def test_user_created_updated_at():
    user = User(chat_id='12345')
    user.save()

    assert user.created_at == datetime(2030, 1, 15)
    assert user.updated_at == datetime(2030, 1, 15)


@freeze_time('2030-01-15')
def test_user_updated_at_changing():
    user = User(chat_id='123456')
    user.save()

    assert user.updated_at == datetime(2030, 1, 15)

    with freeze_time('2030-06-15'):
        user.full_name = 'Oh my dummy'
        user.save()
        assert user.updated_at == datetime(2030, 6, 15)
        assert user.created_at == datetime(2030, 1, 15)


@freeze_time('2030-01-15')
def test_log_command_item_created_at(bot_user):
    lci = LogCommandItem(user=bot_user, command='/start')
    lci.save()

    assert lci.created_at == datetime(2030, 1, 15)


@freeze_time('2030-01-15')
def test_log_command_item_created_at_existing(bot_user):
    lci = LogCommandItem(user=bot_user, command='/start')
    lci.save()

    with freeze_time('2030-06-15'):
        lci.message = 'Oh my dummy'
        lci.save()
        assert lci.created_at == datetime(2030, 1, 15)


def test_telegram_update_fixture_message(telegram_update):
    update = telegram_update(message='Um, hi!')

    assert update.message.text == 'Um, hi!'


def test_telegram_update_fixture_command(telegram_update):
    update = telegram_update(command='/start')

    assert update.message.text == '/start'


def test_user_get_by_update_empty(telegram_update):
    update = telegram_update(message='Um, hi!')

    user = user_get_by_update(update)

    assert isinstance(user, User)
    assert user.chat_id == 383716
    assert user.user_name == 'hemantic'
    assert user.full_name == 'Артём Киселёв'


def test_user_get_by_update_without_surname(telegram_update_without_surname):
    update = telegram_update_without_surname()

    user = user_get_by_update(update)

    assert isinstance(user, User)
    assert user.chat_id == 246225
    assert user.user_name == 'username'
    assert user.full_name == 'Vadim'


def test_user_get_by_update_username_changed(telegram_update):
    user = User(chat_id='383716', user_name='dummy', full_name='John Doe')
    user.save()

    update = telegram_update()

    user = user_get_by_update(update)

    assert isinstance(user, User)
    assert user.chat_id == 383716
    assert user.user_name == 'hemantic'


def test_user_log_command(bot_user):
    log_command(bot_user, '/start', 'Hi')
    log_command(bot_user, '/stop', 'Bye')

    all_commands = LogCommandItem.filter(user=bot_user.chat_id)

    assert all_commands.count() == 2
    assert all_commands.first().message == 'Hi'


def test_today_catalog_requests_count(bot_user, create_telegram_command_logs):
    create_telegram_command_logs(2, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')
    assert bot_user.today_catalog_requests_count() == 2


def test_today_catalog_requests_count_with_empty_statuses(bot_user, create_telegram_command_logs):
    create_telegram_command_logs(2, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')
    create_telegram_command_logs(2, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/', '')

    assert bot_user.today_catalog_requests_count() == 2


def test_catalog_requests_left_count(bot_user, create_telegram_command_logs):
    create_telegram_command_logs(3, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')
    assert bot_user.catalog_requests_left_count() == 0


def test_catalog_requests_count_resetting(bot_user, create_telegram_command_logs):
    with freeze_time('2030-06-15 01:20:00'):
        create_telegram_command_logs(1, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-15 01:30:00'):
        create_telegram_command_logs(1, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-15 01:40:00'):
        create_telegram_command_logs(1, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-16 01:19:59'):
        assert bot_user.can_send_more_catalog_requests() is False

    with freeze_time('2030-06-16 01:20:01'):
        assert bot_user.can_send_more_catalog_requests() is True


def test_normal_user_can_send_catalog_requests(bot_user):
    assert bot_user.can_send_more_catalog_requests() is True


def test_blocked_user_can_not_send_requests(bot_user):
    bot_user.catalog_requests_blocked = True
    assert bot_user.can_send_more_catalog_requests() is False


def test_throttled_user(bot_user, create_telegram_command_logs):
    create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')
    assert bot_user.can_send_more_catalog_requests() is False


@pytest.mark.parametrize('log_count, expected_date', [
    [0, datetime(2030, 1, 15, 1, 30)],
    [3, datetime(2030, 1, 16, 1, 30)],
    [5, datetime(2030, 1, 16, 1, 30)],
])
@freeze_time('2030-01-15 01:30:00')
def test_next_free_catalog_request_time_no_logs(bot_user, create_telegram_command_logs, log_count, expected_date):
    create_telegram_command_logs(log_count, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    assert bot_user.next_free_catalog_request_time() == expected_date


def test_next_free_catalog_request_time_no_logs_tricky(bot_user, create_telegram_command_logs):
    with freeze_time('2030-06-15 01:20:00'):
        create_telegram_command_logs(1, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-15 01:30:00'):
        create_telegram_command_logs(1, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    with freeze_time('2030-06-15 01:40:00'):
        create_telegram_command_logs(3, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/')

    assert bot_user.next_free_catalog_request_time() == datetime(2030, 6, 16, 1, 20)


def test_get_subscribed_to_wb_categories_updates_subscribed(bot_user):
    bot_user.subscribe_to_wb_categories_updates = True
    bot_user.save()

    subscribed_users = get_subscribed_to_wb_categories_updates()

    assert subscribed_users.count() == 1
    assert subscribed_users[0] == bot_user


def test_get_subscribed_to_wb_categories_updates_not_subscribed(bot_user):
    bot_user.subscribe_to_wb_categories_updates = False
    bot_user.save()

    subscribed_users = get_subscribed_to_wb_categories_updates()

    assert subscribed_users.count() == 0
