from unittest.mock import patch

import pytest
from envparse import env


@pytest.mark.parametrize('message', [
    ['https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty'],
    ['https://www.wildberries.ru/brands/la-belle-femme'],
    ['https://www.wildberries.ru/catalog/0/search.aspx?subject=99&search=сапоги&sort=popular'],
])
@patch('src.tasks.schedule_wb_category_export.apply_async')
def test_command_catalog(mocked_celery_delay, web_app, telegram_json_message, message):
    telegram_json = telegram_json_message(message=str(message))

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_celery_delay.assert_called()


@patch('src.tasks.schedule_wb_category_export.apply_async')
@patch('telegram.Bot.send_message')
def test_command_catalog_throttled(mocked_bot_send_message, mocked_celery_delay, web_app, telegram_json_message, create_telegram_command_logs):
    create_telegram_command_logs(5, 'wb_catalog', 'https://www.wildberries.ru/catalog/knigi-i-diski/kantstovary/tochilki')
    telegram_json = telegram_json_message(message='https://www.wildberries.ru/catalog/dom-i-dacha/tovary-dlya-remonta/instrumenty/magnitnye-instrumenty')

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    assert 'лимит запросов закончился' in mocked_bot_send_message.call_args.kwargs['text']


@pytest.mark.parametrize('message_text, expected_text', [
    ['ℹ️ О сервисе', 'Этот телеграм бот поможет собирать данные о товарах на Wildberries'],
    ['🚀 Увеличить лимит запросов', 'Если вы хотите увеличить или снять лимит запросов'],
    ['Я просто мимокрокодил', 'Непонятная команда']
])
@patch('telegram.Bot.send_message')
def test_reply_messages(mocked_bot_send_message, web_app, telegram_json_message, message_text, expected_text):
    telegram_json = telegram_json_message(message=str(message_text))

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    assert expected_text in mocked_bot_send_message.call_args.kwargs['text']


@pytest.mark.parametrize('command, expected_text', [
    ['/start', 'Этот телеграм бот поможет собирать данные о товарах'],
    ['/help', 'Этот телеграм бот поможет собирать данные о товарах'],
])
@patch('telegram.Bot.send_message')
def test_reply_commands(mocked_reply_text, web_app, telegram_json_command, command, expected_text):
    telegram_json = telegram_json_command(command=command)

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    mocked_reply_text.assert_called()
    assert expected_text in mocked_reply_text.call_args.kwargs['text']


@pytest.mark.parametrize('callback, expected_text', [
    ['keyboard_help_catalog_link', 'скопируйте из адресной строки браузера ссылку'],
    ['keyboard_analyse_category', 'Анализ выбранной категории'],
    ['keyboard_help_info_feedback', 'напишите нам весточку'],
])
@patch('telegram.Bot.send_message')
def test_reply_callbacks(mocked_bot_send_message, web_app, telegram_json_callback, callback, expected_text):
    telegram_json = telegram_json_callback(callback=callback)

    web_app.simulate_post('/' + env('TELEGRAM_API_TOKEN'), body=telegram_json)

    assert expected_text in mocked_bot_send_message.call_args.kwargs['text']