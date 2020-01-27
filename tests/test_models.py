from freezegun import freeze_time

from src.models import *


def test_user_create():
    u = user_get_or_created(chat_id='1234')

    assert isinstance(u, User)
    assert u.chat_id == 1234


def test_user_fetch_existing():
    existing_user = User(chat_id='1234')
    existing_user.save()

    requested_user = user_get_or_created(chat_id='1234')

    assert existing_user == requested_user


@freeze_time("2030-01-15")
def test_user_created_updated_at():
    u = user_get_or_created(chat_id='12345')

    assert u.created_at == datetime.datetime(2030, 1, 15)
    assert u.updated_at == datetime.datetime(2030, 1, 15)


@freeze_time("2030-01-15")
def test_user_updated_at_changing():
    u = user_get_or_created(chat_id='123456')

    assert u.updated_at == datetime.datetime(2030, 1, 15)

    with freeze_time("2030-06-15"):
        u.full_name = 'Oh my dummy'
        u.save()
        assert u.updated_at == datetime.datetime(2030, 6, 15)