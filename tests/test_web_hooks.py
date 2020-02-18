from unittest.mock import MagicMock, patch

import pytest
from envparse import env


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
    got = web_app.simulate_post('/callback/wb_category_export')
    assert got.status_code == 500
    assert 'wrong_chat_id' in got.text


@patch('src.tasks.calculate_wb_category_stats.apply_async')
@patch('telegram.Bot.send_message')
def test_category_export_finished_hook_correct(mocked_send_message, mocked_calculate_category_stats, web_app):
    got = web_app.simulate_post('/callback/wb_category_export', params={'chat_id': 100500})

    mocked_calculate_category_stats.assert_called_once()
    mocked_send_message.assert_called_once()
    assert got.status_code == 200
    assert 'ok' in got.text


@patch('src.tasks.calculate_wb_category_diff.apply_async')
def test_category_list_hook(mocked_calculate_diff, web_app):
    got = web_app.simulate_post('/callback/category_list')

    mocked_calculate_diff.assert_called()
    assert got.status_code == 200
    assert 'ok' in got.text


@patch('telegram.ext.Dispatcher.process_update')
@patch('telegram.Update.de_json')
def test_telegram_webhook(mocked_de_json, mocked_process_update, web_app):
    with open('tests/mocks/tg_request_text.json') as f:
        json_body = f.read()
        got = web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=json_body)

        mocked_de_json.assert_called()
        mocked_process_update.assert_called()
        assert got.status_code == 200


def test_index_page(web_app):
    got = web_app.simulate_get('/')

    assert got.status_code == 200
    assert 'lucky_you' in got.text
