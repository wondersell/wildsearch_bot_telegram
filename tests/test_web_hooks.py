from unittest.mock import MagicMock, patch

import pytest
from falcon import testing
from envparse import env

import src.web
import pathlib


@pytest.fixture()
def web_app():
    return testing.TestClient(src.web.app)


@pytest.fixture()
def bot_app(bot):
    """Our bot app, adds the magic curring `call` method to call it with fake bot"""
    from src import bot as bot_methods
    setattr(bot_methods, 'call', lambda method, *args, **kwargs: getattr(bot_methods, method)(bot, *args, **kwargs))
    return bot_methods


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


@patch('telegram.ext.Dispatcher.process_update')
@patch('telegram.Update.de_json')
def test_telegram_webhook(mocked_de_json, mocked_process_update, web_app):
    with open('tests/sample_telegram_request.json') as f:
        json_body = f.read()
        got = web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=json_body)

        mocked_de_json.assert_called()
        mocked_process_update.assert_called()
        assert got.status_code == 200


def test_index_page(web_app):
    got = web_app.simulate_get('/')

    assert got.status_code == 200
    assert 'lucky_you' in got.text
