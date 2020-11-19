import json
import os
import re
from os import environ
from unittest.mock import patch

import mongoengine as me
import peewee as pw
import pytest
import requests_mock
from botocore.stub import Stubber
from envparse import env
from falcon import testing
from telegram import Bot, Update

from src import helpers
from src.models import User, log_command

from seller_stats.utils.loaders import ScrapinghubLoader


@pytest.fixture()
def current_path():
    return os.path.dirname(os.path.abspath(__file__))


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
def telegram_json_message_without_surname():
    def _telegram_json_message(message=None):
        with open('tests/mocks/tg_request_text_without_surname.json') as f:
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
def telegram_update_without_surname(telegram_json_message_without_surname):
    def _telegram_update():
        telegram_json = telegram_json_message_without_surname()

        bot = Bot(env('TELEGRAM_API_TOKEN'))
        update = Update.de_json(json.loads(telegram_json), bot)

        return update

    return _telegram_update


@pytest.fixture
def create_telegram_command_logs(bot_user):
    def _create_telegram_catalog_logs(logs_count=1, command='/start', message='message', status='success'):
        for _ in range(logs_count):
            cmd = log_command(bot_user, command, message)
            cmd.set_status(status)

    return _create_telegram_catalog_logs


@pytest.fixture()
def sample_category_data_raw(current_path):
    def _sample_category_data_raw(source='wb_raw'):
        return open(current_path + f'/mocks/scrapinghub_items_{source}.msgpack', 'rb').read()

    return _sample_category_data_raw


@pytest.fixture()
def set_scrapinghub_requests_mock(requests_mock, sample_category_data_raw):
    def _set_scrapinghub_requests_mock(pending_count=1, running_count=1, job_id='123/1/2', result_source='wb_raw'):
        requests_mock.get('https://storage.scrapinghub.com/ids/414324/spider/wb', text='1')
        requests_mock.get('https://storage.scrapinghub.com/ids/414324/spider/ozon', text='1')
        requests_mock.get('https://storage.scrapinghub.com/jobq/414324/count?state=pending&spider=wb', text=f'{pending_count}')
        requests_mock.get('https://storage.scrapinghub.com/jobq/414324/count?state=running&spider=wb', text=f'{running_count}')
        requests_mock.post('https://app.scrapinghub.com/api/run.json', json={'status': 'ok', 'jobid': f'{job_id}'})
        requests_mock.get(f'https://storage.scrapinghub.com/items/{job_id}?meta=_key', content=sample_category_data_raw(source=result_source), headers={'Content-Type': 'application/x-msgpack; charset=UTF-8'})
        requests_mock.get(f'https://storage.scrapinghub.com/jobs/{job_id}/state', text='"finished"')

    return _set_scrapinghub_requests_mock


@pytest.fixture()
def scrapinghub_dataset(set_scrapinghub_requests_mock):
    def _scrapinghub_dataset(job_id, result_source):
        set_scrapinghub_requests_mock(result_source=result_source)

        slug, marketplace, transformer = helpers.detect_mp_by_job_id(job_id=job_id)

        return ScrapinghubLoader(job_id=job_id, transformer=transformer).load()

    return _scrapinghub_dataset


@pytest.fixture
def web_app():
    with patch('src.bot.reset_webhook'):
        from src import web
        return testing.TestClient(web.app)


@pytest.fixture(autouse=True)
def s3_stub():
    with Stubber(helpers.s3) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture(autouse=True)
def mongo(request):
    me.connection.disconnect()
    me.connect('mongotest', host='mongomock://localhost')


@pytest.fixture
def db():
    return pw.SqliteDatabase(':memory:')


@pytest.fixture(autouse=True)
def models(db):
    """Emulate the transaction -- create a new db before each test and flush it after.
    Also, return the app.models module"""
    from src import models
    app_models = [models.User, models.LogCommandItem]

    db.bind(app_models, bind_refs=False, bind_backrefs=False)
    db.connect()
    db.create_tables(app_models)

    yield models

    db.drop_tables(app_models)
    db.close()


@pytest.fixture(autouse=True)
def requests_mocker():
    """Mock all requests.
    This is an autouse fixture so that tests can't accidentally
    perform real requests without being noticed.
    """
    with requests_mock.Mocker() as m:
        m.post('https://api.amplitude.com/2/httpapi', json={'code': 200})
        m.post(re.compile('https://api.airtable.com/v0/'), json={'code': 200})
        yield m


@pytest.fixture()
def bot_user():
    user = User.create(
        chat_id=383716,
        user_name='wildsearch_test_user',
        full_name='Wonder Sell',
    )

    return user


@pytest.fixture()
def set_amplitude():
    environ['AMPLITUDE_API_KEY'] = 'dummy_amplitude_key'
