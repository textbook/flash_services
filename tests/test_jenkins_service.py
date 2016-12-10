from datetime import datetime
from unittest import mock
from urllib.parse import quote_plus

import pytest

from flash_services import Jenkins, SERVICES


@pytest.fixture
def service():
    return SERVICES['jenkins'](
        username='foo',
        password='bar',
        root='https://test.org',
        job='baz',
    )


def test_correct_config():
    assert Jenkins.REQUIRED == {'username', 'password', 'root', 'job'}
    assert Jenkins.TEMPLATE == 'ci-section'


@mock.patch('flash_services.jenkins.logger.debug')
@mock.patch('flash_services.jenkins.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': {'builds': [], 'name': 'baz'},
})
def test_update_success(get, debug, service):
    result = service.update()

    get.assert_called_once_with(
        'https://test.org/job/baz/api/json?tree={}'.format(
            quote_plus(Jenkins.TREE_PARAMS)
        ),
        headers={'Authorization': 'Basic Zm9vOmJhcg=='}
    )
    debug.assert_called_once_with('fetching Jenkins project data')
    assert result == {'builds': [], 'name': 'baz', 'health': 'neutral'}


@mock.patch('flash_services.jenkins.logger.error')
@mock.patch('flash_services.jenkins.requests.get', **{
    'return_value.status_code': 401,
})
def test_update_failure(_, error, service):
    result = service.update()

    error.assert_called_once_with('failed to update Jenkins project data')
    assert result == {}


def test_formatting():
    response = dict(
        name='foo',
        builds=[dict(
            duration=31698,
            description=None,
            timestamp=1481387964313,
            result='SUCCESS',
            changeSets=[
                dict(items=[dict(comment='hello', author=dict(fullName='who'))])
            ]
        )],
    )

    result = Jenkins.format_data(response)

    assert result == dict(
        name='foo',
        builds=[dict(
            author='who',
            duration=31,
            elapsed='took 31 seconds',
            message='hello',
            outcome='passed',
            started_at=1481387964,
        )],
        health='ok',
    )


@mock.patch('flash_services.jenkins.time.time', return_value=1481387969.3)
def test_unfinished_formatting(_, service):
    response = dict(
        name='foo',
        builds=[dict(
            duration=0,
            description=None,
            timestamp=1481387964313,
            result=None,
            changeSets=[],
        )],
    )

    result = service.format_data(response)

    assert result == dict(
        name='foo',
        builds=[dict(
            author='&lt;no author&gt;',
            duration=5,
            elapsed='estimate not available',
            message='&lt;no message&gt;',
            outcome='working',
            started_at=1481387964,
        )],
        health='neutral',
    )


@mock.patch('flash_services.utils.datetime', **{
    'now.return_value': (datetime.fromtimestamp(1481387969)),
    'fromtimestamp.side_effect': datetime.fromtimestamp,
})
@mock.patch('flash_services.jenkins.time.time', return_value=1481387969.3)
def test_estimated_formatting(_, __, service):
    response = dict(name='foo', builds=[
        dict(duration=0, description=None, timestamp=1481387964313, result=None),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
        dict(duration=10000, description=None, timestamp=1481387964313, result='SUCCESS'),
    ])

    result = service.format_data(response)

    assert result['builds'][0] == dict(
        author='&lt;no author&gt;',
        duration=5,
        elapsed='five seconds left',
        message='&lt;no message&gt;',
        outcome='working',
        started_at=1481387964,
    )
