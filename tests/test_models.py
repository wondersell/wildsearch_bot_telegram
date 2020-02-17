from freezegun import freeze_time

from src.models import *


def test_user_get_by_chat_id():
    u_created = User(chat_id='1234').save()

    u_fetched = user_get_by(chat_id='1234')

    assert u_created == u_fetched


def test_user_get_by_chat_id_existing(bot_user):
    bot_user.save()
    u_fetched = user_get_by(chat_id='383716')  # magic number from tests/mocks/tg_request_command.json

    assert u_fetched == bot_user


@freeze_time("2030-01-15")
def test_user_created_updated_at():
    u = User(chat_id='12345').save()

    assert u.created_at == datetime(2030, 1, 15)
    assert u.updated_at == datetime(2030, 1, 15)


@freeze_time("2030-01-15")
def test_user_updated_at_changing():
    u = User(chat_id='123456').save()

    assert u.updated_at == datetime(2030, 1, 15)

    with freeze_time("2030-06-15"):
        u.full_name = 'Oh my dummy'
        u.save()
        assert u.updated_at == datetime(2030, 6, 15)
        assert u.created_at == datetime(2030, 1, 15)


@freeze_time("2030-01-15")
def test_log_command_item_created_at():
    lci = LogCommandItem(command='/start').save()

    assert lci.created_at == datetime(2030, 1, 15)


@freeze_time("2030-01-15")
def test_log_command_item_created_at_existing():
    lci = LogCommandItem(command='/start').save()

    with freeze_time("2030-06-15"):
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


def test_user_log_command(bot_user):
    log_command(bot_user, '/start', 'Hi')
    log_command(bot_user, '/stop', 'Bye')

    all_commands = LogCommandItem.objects(user=bot_user.id)

    assert all_commands.count() == 2
    assert all_commands.first()['message'] == 'Hi'


def test_today_catalog_requests_count(bot_user, create_telegram_command_logs):
    create_telegram_command_logs(4, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/kantstovary/tochilki')
    assert bot_user.today_catalog_requests_count() == 4


def test_normal_user_can_send_catalog_requests(bot_user):
    assert bot_user.can_send_more_catalog_requests() is True


def test_blocked_user_can_not_send_requests(bot_user):
    bot_user.catalog_requests_blocked = True
    assert bot_user.can_send_more_catalog_requests() is False


def test_throttled_user(bot_user, create_telegram_command_logs):
    create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/kantstovary/tochilki')
    assert bot_user.can_send_more_catalog_requests() is False
