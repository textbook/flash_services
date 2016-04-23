from unittest import mock

import pytest

from flash_services.core import Service
from flash_services.travis import TravisOS


@pytest.fixture()
def service():
    return TravisOS(account='foo', app='bar')

HEADERS = {
    'Accept': 'application/vnd.travis-ci.2+json',
    'User-Agent': 'Flash',
}


def test_tracker_service_type():
    assert issubclass(TravisOS, Service)


def test_correct_config():
    assert TravisOS.REQUIRED == {'app', 'account'}
    assert TravisOS.ROOT == 'https://api.travis-ci.org'
    assert TravisOS.TEMPLATE == 'ci-section'


def test_correct_headers(service):
    assert service.headers == HEADERS


@mock.patch('flash_services.travis.logger.debug')
@mock.patch('flash_services.travis.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': {},
})
def test_update_success(get, debug, service):
    result = service.update()

    get.assert_called_once_with(
        'https://api.travis-ci.org/repos/foo/bar/builds',
        headers=HEADERS,
    )
    debug.assert_called_once_with('fetching Travis CI project data')
    assert result == {'builds': [], 'name': 'foo/bar', 'health': 'neutral'}


@mock.patch('flash_services.travis.logger.error')
@mock.patch('flash_services.travis.requests.get', **{
    'return_value.status_code': 401,
})
def test_update_failure(get, error, service):
    result = service.update()

    get.assert_called_once_with(
        'https://api.travis-ci.org/repos/foo/bar/builds',
        headers=HEADERS,
    )
    error.assert_called_once_with('failed to update Travis CI project data')
    assert result == {}


def test_formatting(service):
    response = dict(
        builds=[dict(
            commit_id=123456,
            finished_at='2016-04-14T20:57:07Z',
            started_at='2016-04-14T20:47:40Z',
            state='passed',
        )],
        commits=[dict(
            author_name='alice',
            id=123456,
            message='hello world',
        )],
    )

    result = service.format_data(response)

    assert result == dict(
        name='foo/bar',
        builds=[dict(
            author='alice',
            duration=567,
            elapsed='took nine minutes',
            message='hello world',
            outcome='passed',
            started_at=1460666860,
        )],
        health='ok',
    )


@mock.patch('flash_services.core.logger.warning')
def test_unfinished_formatting(warning, service):
    response = dict(
        builds=[dict(
            commit_id=123456,
            state='garbage',
        )],
        commits=[dict(
            author_name='alice',
            id=123456,
            message='some much longer message',
        )],
    )

    result = service.format_data(response)

    assert result == dict(
        name='foo/bar',
        builds=[dict(
            author='alice',
            duration=None,
            elapsed='elapsed time not available',
            message='some much longer...',
            outcome=None,
            started_at=None,
        )],
        health='neutral',
    )
    warning.assert_called_once_with('unknown outcome: %s', 'garbage')
