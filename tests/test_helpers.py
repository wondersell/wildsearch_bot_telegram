from json import loads

import pytest
import requests_mock
from seller_stats.utils.transformers import WildsearchCrawlerOzonTransformer as ozon_transformer
from seller_stats.utils.transformers import WildsearchCrawlerWildberriesTransformer as wb_transformer

from src.helpers import (AmplitudeLogger, detect_mp_by_job_id, get_digits_text, smart_format_number,
                         smart_format_prettify, smart_format_round_hard, smart_format_round_super_hard)


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
    [1432, ('1\u00A0400', '')],
    [5899, ('5\u00A0900', '')],
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
    [3985300123427720, ['3\u00A0985\u00A0300\u00A0123\u00A0427\u00A0720', '']],
])
def test_smart_format_number(test_number, expected):
    number, digits = smart_format_number(test_number)

    assert number == expected[0]
    assert digits == expected[1]


@pytest.mark.parametrize('test_number, expected', [
    [5, ''],
    [14, ''],
    [563, ''],
    [1354, ''],
    [54325, 'тыс.'],
    [896123, 'тыс.'],
    [6743104, 'млн.'],
    [44671232, 'млн.'],
    [413241514, 'млн.'],
    [7879023423, 'млрд.'],
    [46123412341, 'млрд.'],
    [123823412340, 'млрд.'],
    [3979812341234, 'трлн.'],
    [52435123424351, 'трлн.'],
    [234815285182350, 'трлн.'],
    [2348152851823500, ''],
])
def test_get_digits_text_regular(test_number, expected):
    assert get_digits_text(test_number) == expected


@pytest.mark.parametrize('test_number, expected', [
    [5, ''],
    [14, ''],
    [563, ''],
    [1354, 'тыс.'],
    [54325, 'тыс.'],
    [896123, 'тыс.'],
    [6743104, 'млн.'],
    [44671232, 'млн.'],
    [413241514, 'млн.'],
    [7879023423, 'млрд.'],
    [46123412341, 'млрд.'],
    [123823412340, 'млрд.'],
    [3979812341234, 'трлн.'],
    [52435123424351, 'трлн.'],
    [234815285182350, 'трлн.'],
    [2348152851823500, ''],
])
def test_get_digits_text_not_skip_thousends(test_number, expected):
    assert get_digits_text(test_number, skip_thousands=False) == expected


@pytest.mark.parametrize('test_number, expected', [
    [413241514, '413\u00A0241\u00A0514'],
    [34, '34'],
    [68.86623, '68,87'],
    [141341.3876, '141\u00A0341,39'],
])
def test_smart_format_prettify(test_number, expected):
    assert smart_format_prettify(test_number) == expected


@pytest.mark.parametrize('test_number, expected', [
    [5, (5, 5)],
    [14, (10, 10)],
    [82, (80, 80)],
    [133, (130, 130)],
    [563, (560, 560)],
    [1354, (1, 1000)],
    [1432, (1, 1000)],
    [5899, (6, 6000)],
    [45037, (50, 50000)],
    [54325, (50, 50000)],
    [79637, (80, 80000)],
    [673912, (670, 670000)],
    [318642, (320, 320000)],
    [498177, (500, 500000)],
    [896123, (900, 900000)],
    [1387400, (1, 1000000)],
    [6743104, (7, 7000000)],
    [44671232, (40, 40000000)],
    [58787306, (60, 60000000)],
    [413241514, (410, 410000000)],
    [679347200, (680, 680000000)],
    [3438209796, (3, 3000000000)],
    [7879023423, (8, 8000000000)],
    [46123412341, (50, 50000000000)],
    [53084768109, (50, 50000000000)],
    [123823412340, (120, 120000000000)],
    [156084768109, (160, 160000000000)],
])
def test_smart_format_round_hard(test_number, expected):
    number, digits = smart_format_round_hard(test_number)

    assert number == expected[0]
    assert digits == expected[1]


def test_smart_format_round_hard_handling_floats():
    number, digits = smart_format_round_hard(710356.5492067898)

    assert number == 710
    assert digits == 710000


@pytest.mark.parametrize('test_number, expected', [
    [5, (5, 5)],
    [14, (20, 20)],
    [82, (90, 90)],
    [133, (200, 200)],
    [563, (600, 600)],
    [1354, (2, 2000)],
    [1432, (2, 2000)],
    [5899, (6, 6000)],
    [45037, (50, 50000)],
    [54325, (60, 60000)],
    [79637, (80, 80000)],
    [673912, (700, 700000)],
    [318642, (400, 400000)],
    [498177, (500, 500000)],
    [896123, (900, 900000)],
    [1387400, (2, 2000000)],
    [6743104, (7, 7000000)],
    [44671232, (50, 50000000)],
    [58787306, (60, 60000000)],
    [413241514, (500, 500000000)],
    [679347200, (700, 700000000)],
    [3438209796, (4, 4000000000)],
    [7879023423, (8, 8000000000)],
    [46123412341, (50, 50000000000)],
    [53084768109, (60, 60000000000)],
    [123823412340, (200, 200000000000)],
    [156084768109, (200, 200000000000)],
])
def test_smart_format_round_super_hard(test_number, expected):
    number, digits = smart_format_round_super_hard(test_number)

    assert number == expected[0]
    assert digits == expected[1]
