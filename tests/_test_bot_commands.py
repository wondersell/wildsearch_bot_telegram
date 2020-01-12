from unittest.mock import MagicMock, patch
from src.bot import catalog, rnd
from envparse import env


@patch('telegram.Bot.send_message')
@patch('telegram.Bot.send_document')
@patch('src.bot.rnd')
def test_command_rnd(mocked_command, mocked_send_document, mocked_send_message, web_app):
    with open('tests/mocks/tg_request_text.json') as f:
        json_body = f.read()

        got = web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=json_body)

        mocked_command.assert_called()

