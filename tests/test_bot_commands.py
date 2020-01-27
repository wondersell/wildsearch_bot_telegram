import json
from unittest.mock import patch

import pytest
from envparse import env


def _telegram_json_message(message=None):
    with open('tests/mocks/tg_request_text.json') as f:
        json_body = f.read()
        json_data = json.loads(json_body)

        if message is not None:
            json_data['message']['text'] = message

        return json.dumps(json_data)


def _telegram_json_command(command=None):
    with open('tests/mocks/tg_request_command.json') as f:
        json_body = f.read()
        json_data = json.loads(json_body)

        if command is not None:
            json_data['message']['text'] = command
            json_data['message']['entities'][0]['length'] = len(command)

        return json.dumps(json_data)


@patch('telegram.Message.reply_text')
def test_command_rnd(mocked_reply_text, web_app):
    telegram_json = _telegram_json_message(message='Как дела, потомки?')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()


@pytest.mark.parametrize('message, expected', [
    ['Как дела, потомки?', 'reply_text'],
    ['https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty', 'celery_delay'],
])
@patch('src.tasks.schedule_category_export.delay')
@patch('telegram.Message.reply_text')
def test_command_catalog(mocked_reply_text, mocked_celery_delay, web_app, message, expected):
    telegram_json = _telegram_json_message(message=message)

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    if expected == 'reply_text':
        mocked_reply_text.assert_called()

    if expected == 'celery_delay':
        mocked_celery_delay.assert_called()


@patch('telegram.Message.reply_text')
def test_command_start(mocked_reply_text, web_app):
    telegram_json = _telegram_json_command(command='/start')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()