from freezegun import freeze_time

from src.models import *


def test_user_get_by_chat_id():
    u_created = User(chat_id='1234').save()

    u_fetched = user_get_by(chat_id='1234')

    assert u_created == u_fetched


@freeze_time("2030-01-15")
def test_user_created_updated_at():
    u = User(chat_id='12345').save()

    assert u.created_at == datetime.datetime(2030, 1, 15)
    assert u.updated_at == datetime.datetime(2030, 1, 15)


@freeze_time("2030-01-15")
def test_user_updated_at_changing():
    u = User(chat_id='123456').save()

    assert u.updated_at == datetime.datetime(2030, 1, 15)

    with freeze_time("2030-06-15"):
        u.full_name = 'Oh my dummy'
        u.save()
        assert u.updated_at == datetime.datetime(2030, 6, 15)


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
