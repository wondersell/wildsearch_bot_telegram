import json
from unittest.mock import patch
from telegram import Bot, Update
from src.models import *

import pytest
from envparse import env


@patch('telegram.Message.reply_text')
def test_command_rnd(mocked_reply_text, web_app, telegram_json_message):
    telegram_json = telegram_json_message(message='Как дела, потомки?')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()


@pytest.mark.parametrize('message, expected', [
    ['Как дела, потомки?', 'reply_text'],
    ['https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty', 'celery_delay'],
])
@patch('src.tasks.schedule_category_export.delay')
@patch('telegram.Message.reply_text')
def test_command_catalog(mocked_reply_text, mocked_celery_delay, web_app, telegram_json_message, message, expected):
    telegram_json = telegram_json_message(message=message)

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    if expected == 'reply_text':
        mocked_reply_text.assert_called()

    if expected == 'celery_delay':
        mocked_celery_delay.assert_called()


@patch('telegram.Message.reply_text')
def test_command_start(mocked_reply_text, web_app, telegram_json_command):
    telegram_json = telegram_json_command(command='/start')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()


def test_create_update_from_json_mock(telegram_json_command):
    telegram_json = telegram_json_command(command='/start')

    bot = Bot(env('TELEGRAM_API_TOKEN'))
    update = Update.de_json(json.loads(telegram_json), bot)

    assert isinstance(update, Update)
    assert update.message.text == '/start'
