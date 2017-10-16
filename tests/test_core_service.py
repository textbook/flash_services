from collections import OrderedDict
from datetime import datetime, timezone, timedelta

import pytest

from flash_services.core import Service


class Fake(Service):

    ROOT = 'root/url'

    def __init__(self, *, foo, bar):
        super().__init__()

    def update(self):
        pass


@pytest.mark.parametrize('config', [
    {},
    {'foo': None},
    {'bar': None},
])
def test_required_config(config):
    with pytest.raises(TypeError) as excinfo:
        Fake.from_config(**config)
    message = excinfo.value.args[0]
    assert 'missing required config keys' in message
    assert 'from Fake' in message


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
    assert Fake(foo=None, bar=None).url_builder(*args, **kwargs) == expected


def test_calculate_timeout_delta_seconds():
    assert Service.calculate_timeout('120') == 120


def test_calculate_timeout_http_date():
    three_minutes_later = datetime.now(tz=timezone.utc) + timedelta(minutes=3)
    http_date = '%a, %d %b %Y %H:%M:%S %Z'
    assert 179 <= Service.calculate_timeout(
        three_minutes_later.strftime(http_date),
    ) <= 181


def test_abstract_methods_required():
    with pytest.raises(TypeError):
        class Broken(Service):
            pass
        Broken()
