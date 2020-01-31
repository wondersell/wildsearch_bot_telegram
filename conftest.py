import pytest
import mongoengine as me
import json
from unittest.mock import patch
from falcon import testing
from botocore.stub import Stubber
from telegram import Bot, Update
from src import scrapinghub_helper, web
from envparse import env


@pytest.fixture
def telegram_json_message():
    def _telegram_json_message(message=None):
        with open('tests/mocks/tg_request_text.json') as f:
            json_body = f.read()
            json_data = json.loads(json_body)

            if message is not None:
                json_data['message']['text'] = message

            return json.dumps(json_data)
    return _telegram_json_message


@pytest.fixture
def telegram_json_command():
    def _telegram_json_command(command=None):
        with open('tests/mocks/tg_request_command.json') as f:
            json_body = f.read()
            json_data = json.loads(json_body)

            if command is not None:
                json_data['message']['text'] = command
                json_data['message']['entities'][0]['length'] = len(command)

            return json.dumps(json_data)

    return _telegram_json_command


@pytest.fixture
def telegram_json_callback():
    def _telegram_json_command(callback=None):
        with open('tests/mocks/tg_request_callback.json') as f:
            json_body = f.read()
            json_data = json.loads(json_body)

            if callback is not None:
                json_data['callback_query']['data'] = callback

            return json.dumps(json_data)

    return _telegram_json_command


@pytest.fixture
def telegram_update(telegram_json_message, telegram_json_command, telegram_json_callback):
    def _telegram_update(command=None, message=None, callback=None):
        telegram_json = telegram_json_message()

        if command is not None:
            telegram_json = telegram_json_command(command)

        if message is not None:
            telegram_json = telegram_json_message(message)

        if callback is not None:
            telegram_json = telegram_json_callback(callback)

        bot = Bot(env('TELEGRAM_API_TOKEN'))
        update = Update.de_json(json.loads(telegram_json), bot)

        return update

    return _telegram_update


@pytest.fixture
def web_app():
    return testing.TestClient(web.app)


@pytest.fixture(autouse=True)
def s3_stub():
    with Stubber(scrapinghub_helper.s3) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture(autouse=True)
def mongo(request):
    me.connection.disconnect()
    db = me.connect('mongotest', host='mongomock://localhost')
