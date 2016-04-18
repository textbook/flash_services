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
