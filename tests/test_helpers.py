from json import loads

import pytest
import requests_mock
from seller_stats.utils.transformers import WildsearchCrawlerOzonTransformer as ozon_transformer
from seller_stats.utils.transformers import WildsearchCrawlerWildberriesTransformer as wb_transformer

from src.helpers import AmplitudeLogger, detect_mp_by_job_id, smart_format_number


@pytest.fixture()
def mocked_amplitude():
    return AmplitudeLogger('sample_key')


def test_amplitude_logger_class_init(mocked_amplitude):
    assert mocked_amplitude.endpoint == 'https://api.amplitude.com/2/httpapi'
    assert mocked_amplitude.api_key == 'sample_key'


def tes_amplited_logger_called(mocked_amplitude):
    with requests_mock.Mocker() as m:
        m.post('https://api.amplitude.com/2/httpapi', json={'code': 200})

        mocked_amplitude.log(event='dummy', user_id=1029384756)

        mocked_json = loads(m.request_history[0].text)
        assert mocked_json['events'][0]['user_id'] == 1029384756
        assert mocked_json['events'][0]['event_type'] == 'dummy'
        assert mocked_json['events'][0]['platform'] == 'Telegram'


def test_aplitude_logger_pass_user_properties(mocked_amplitude):
    with requests_mock.Mocker() as m:
        m.post('https://api.amplitude.com/2/httpapi', json={'code': 200})

        mocked_amplitude.log(event='dummy', user_id=1029384756, user_properties={'property1': 'value1'})

        mocked_json = loads(m.request_history[0].text)
        assert mocked_json['events'][0]['user_properties']['property1'] == 'value1'


def test_aplitude_logger_pass_event_properties(mocked_amplitude):
    with requests_mock.Mocker() as m:
        m.post('https://api.amplitude.com/2/httpapi', json={'code': 200})

        mocked_amplitude.log(event='dummy', user_id=1029384756, event_properties={'property1': 'value1'})

        mocked_json = loads(m.request_history[0].text)
        assert mocked_json['events'][0]['event_properties']['property1'] == 'value1'


def test_aplitude_logger_pass_timestamp(mocked_amplitude):
    with requests_mock.Mocker() as m:
        m.post('https://api.amplitude.com/2/httpapi', json={'code': 200})

        mocked_amplitude.log(event='dummy', user_id=1029384756, timestamp='12345678')

        mocked_json = loads(m.request_history[0].text)
        assert mocked_json['events'][0]['time'] == '12345678'


@pytest.mark.parametrize('job_id, expected', [
    ['414324/1/818', ('WB', 'Wildberries', wb_transformer)],
    ['414324/1/95', ('WB', 'Wildberries', wb_transformer)],
    ['414324/1/6', ('WB', 'Wildberries', wb_transformer)],
    ['414324/2/19', ('Ozon', 'Ozon', ozon_transformer)],
    ['414324/2/1', ('Ozon', 'Ozon', ozon_transformer)],
    ['414324/2/735', ('Ozon', 'Ozon', ozon_transformer)],
    ['123123/4345/32', (None, None, None)],
])
def test_detect_mp_by_job_id(job_id, expected):
    slug, marketplace, transformer = detect_mp_by_job_id(job_id)

    assert slug == expected[0]
    assert marketplace == expected[1]

    if expected[2] is not None:
        assert isinstance(transformer, expected[2])
    else:
        assert expected[2] is None


@pytest.mark.parametrize('test_number, expected', [
    [5, ('5', '')],
    [82, ('80', '')],
    [133, ('130', '')],
    [1432, ('1 400', '')],
    [5899, ('5 900', '')],
    [45037, ('45', 'тыс.')],
    [79637, ('80', 'тыс.')],
    [498177, ('498', 'тыс.')],
    [1387400, ('1,4', 'млн.')],
    [58787306, ('58,8', 'млн.')],
    [679347200, ('679', 'млн.')],
    [3438209796, ('3,4', 'млрд.')],
    [56084768109, ('56,1', 'млрд.')],
    [156084768109, ('156', 'млрд.')],
    [6471309583998, ['6,5', 'трлн.']],
    [22489066284578, ['22,5', 'трлн.']],
    [982578123334900, ['983', 'трлн.']],
    [3985300123427720, ['3 985 300 123 427 720', '']],
])
def test_smart_format_number(test_number, expected):
    number, digits = smart_format_number(test_number)

    assert number == expected[0]
    assert digits == expected[1]
