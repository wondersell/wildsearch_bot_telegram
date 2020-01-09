from unittest.mock import MagicMock, patch

import pytest
from falcon import testing

import src.web


@pytest.fixture()
def web_app():
    return testing.TestClient(src.web.app)


@pytest.fixture()
def bot_app(bot):
    """Our bot app, adds the magic curring `call` method to call it with fake bot"""
    from src import app
    setattr(app, 'call', lambda method, *args, **kwargs: getattr(app, method)(bot, *args, **kwargs))
    return app


@pytest.fixture
def bot():
    """Mocked instance of the bot"""
    class Bot:
        send_message = MagicMock()

    return Bot()


def test_category_export_finished_hook_missing_chat_id(web_app, bot):
    got = web_app.simulate_post('/callback/category_export')
    assert got.status_code == 500
    assert 'wrong_chat_id' in got.text


@patch('telegram.Bot.send_message')
def test_category_export_finished_hook_correct(mocked_send_message, web_app):
    got = web_app.simulate_post('/callback/category_export', params={'chat_id': 100500})

    mocked_send_message.assert_called_once()
    assert got.status_code == 200
    assert 'ok' in got.text


@patch('telegram.Bot.send_message')
@patch('telegram.Bot.send_document')
def test_category_list_hook(mocked_send_document, mocked_send_message, web_app):
    got = web_app.simulate_post('/callback/category_list')

    mocked_send_message.assert_called()
    assert got.status_code == 200
    assert 'ok' in got.text