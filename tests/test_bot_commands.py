import json
from unittest.mock import patch
from telegram import Bot, Update
from src.models import *

import pytest
from envparse import env


@patch('telegram.Bot.send_message')
def test_command_rnd(mocked_reply_text, web_app, telegram_json_message):
    telegram_json = telegram_json_message(message='Как дела, потомки?')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()


@pytest.mark.parametrize('message, expected', [
    ['Как дела, потомки?', 'reply_text'],
    ['https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty', 'celery_delay'],
])
@patch('src.tasks.schedule_wb_category_export.apply_async')
@patch('telegram.Bot.send_message')
def test_command_catalog(mocked_reply_text, mocked_celery_delay, web_app, telegram_json_message, message, expected):
    telegram_json = telegram_json_message(message=message)

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    if expected == 'reply_text':
        mocked_reply_text.assert_called()

    if expected == 'celery_delay':
        mocked_celery_delay.assert_called()


@patch('src.tasks.schedule_wb_category_export.apply_async')
@patch('telegram.Bot.send_message')
def test_command_catalog_normal(mocked_reply_text, mocked_celery_delay, web_app, telegram_json_message):
    telegram_json = telegram_json_message(message='https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_celery_delay.assert_called()


@patch('src.tasks.schedule_wb_category_export.apply_async')
@patch('telegram.Bot.send_message')
def test_command_catalog_throttled(mocked_reply_text, mocked_celery_delay, web_app, telegram_json_message, create_telegram_command_logs):
    create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/kantstovary/tochilki')
    telegram_json = telegram_json_message(message='https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    assert 'лимит запросов закончился' in mocked_reply_text.call_args.kwargs['text']


@patch('telegram.Bot.send_message')
def test_command_start(mocked_reply_text, web_app, telegram_json_command):
    telegram_json = telegram_json_command(command='/start')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()
    assert 'Этот телеграм бот поможет собирать данные о товарах' in mocked_reply_text.call_args.kwargs['text']


def test_create_update_from_json_mock(telegram_json_command):
    telegram_json = telegram_json_command(command='/start')

    bot = Bot(env('TELEGRAM_API_TOKEN'))
    update = Update.de_json(json.loads(telegram_json), bot)

    assert isinstance(update, Update)
    assert update.message.text == '/start'


@patch('telegram.Bot.send_message')
@patch('logging.Logger.info')
def test_command_analyse_category(mocked_logger_info, mocked_bot_send_message, web_app, telegram_json_callback):
    telegram_json = telegram_json_callback(callback='keyboard_analyse_category')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    #mocked_bot_send_message.assert_called()
    mocked_logger_info.assert_called_with('Analyse category command received')


@patch('telegram.Bot.send_message')
@patch('logging.Logger.info')
def test_command_info(mocked_logger_info, mocked_bot_send_message, web_app, telegram_json_message):
    telegram_json = telegram_json_message(message='ℹ️ О сервисе')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_bot_send_message.assert_called()
    mocked_logger_info.assert_called_with('Info command received')
