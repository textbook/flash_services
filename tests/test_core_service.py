from collections import OrderedDict
from datetime import datetime

import pytest

from flash_services.core import Service


class Test(Service):

    REQUIRED = {'foo', 'bar'}
    ROOT = 'root/url'

    def __init__(self):
        super().__init__()

    def update(self):
        pass


@pytest.mark.parametrize('config', [
    ({},),
    ({'foo': None},),
    ({'bar': None},),
])
def test_required_config(config):
    with pytest.raises(TypeError):
        Test.from_config(**config)


@pytest.mark.parametrize('args, kwargs, expected', [
    (('/endpoint',), {}, 'root/url/endpoint'),
    (('/endpoint/{foo}',), {'params': {'foo': 'bar'}}, 'root/url/endpoint/bar'),
    (('/endpoint',), {'url_params': {'foo': 'bar'}}, 'root/url/endpoint?foo=bar'),
    (
        ('/endpoint',),
        {'url_params': OrderedDict([('foo', 'bar'), ('bar', 'baz')])},
        'root/url/endpoint?foo=bar&bar=baz',
    ),
    (
        ('/endpoint/{hello}',),
        {
            'params': {'hello': 'world'},
            'url_params': OrderedDict([('foo', 'bar'), ('bar', 'baz')]),
        },
        'root/url/endpoint/world?foo=bar&bar=baz',
    ),
])
def test_url_builder(args, kwargs, expected):
    assert Test().url_builder(*args, **kwargs) == expected


def test_build_estimate_unstarted():
    current = {'started_at': None}

    Service.estimate_time(current, [])

    assert current['elapsed'] == 'estimate not available'


def test_build_estimate_no_history():
    current = {'started_at': 123456789}

    Service.estimate_time(current, [])

    assert current['elapsed'] == 'estimate not available'


def test_build_estimate_usable():
    current = {'started_at': int(datetime.now().timestamp())}
    previous = [
        {'outcome': 'passed', 'duration': 610},
        {'outcome': 'passed', 'duration': 600},
        {'outcome': 'passed', 'duration': 605},
    ]

    Service.estimate_time(current, previous)

    assert current['elapsed'] == 'ten minutes left'


def test_build_estimate_negative():
    current = {'started_at': int(datetime.now().timestamp())}
    previous = [
        {'outcome': 'passed', 'duration': -5},
        {'outcome': 'passed', 'duration': -10},
        {'outcome': 'passed', 'duration': 0},
    ]

    Service.estimate_time(current, previous)

    assert current['elapsed'] == 'nearly done'
