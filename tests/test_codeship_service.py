from unittest import mock

import pytest

from flash_services.core import Service
from flash_services.codeship import Codeship


@pytest.fixture()
def service():
    return Codeship(api_token='foobar', project_id=123)


def test_tracker_service_type():
    assert issubclass(Codeship, Service)


def test_correct_config():
    assert Codeship.AUTH_PARAM == 'api_key'
    assert Codeship.REQUIRED == {'api_token', 'project_id'}
    assert Codeship.ROOT == 'https://codeship.com/api/v1'
    assert Codeship.TEMPLATE == 'codeship'


@mock.patch('flash_services.codeship.logger.debug')
@mock.patch('flash_services.codeship.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': {'repository_name': 'bar'},
})
def test_update_success(get, debug, service):
    result = service.update()

    get.assert_called_once_with(
        'https://codeship.com/api/v1/projects/123.json?api_key=foobar',
    )
    debug.assert_called_once_with('fetching Codeship project data')
    assert result == {'builds': [], 'name': 'bar', 'health': 'neutral'}


@mock.patch('flash_services.codeship.logger.error')
@mock.patch('flash_services.codeship.requests.get', **{
    'return_value.status_code': 401,
})
def test_update_failure(get, error, service):
    result = service.update()

    get.assert_called_once_with(
        'https://codeship.com/api/v1/projects/123.json?api_key=foobar',
    )
    error.assert_called_once_with('failed to update Codeship project data')
    assert result == {}


def test_formatting():
    response = dict(
        repository_name='foo',
        builds=[dict(
            finished_at='2016-04-01T23:10:06.334Z',
            github_username='textbook',
            message='hello world',
            started_at='2016-04-01T23:04:03.050Z',
            status='success',
        )],
    )

    result = Codeship.format_data(response)

    assert result == dict(
        name='foo',
        builds=[dict(
            author='textbook',
            duration=363,
            elapsed='took six minutes',
            message='hello world',
            outcome='passed',
            started_at=1459551843,
        )],
        health='ok',
    )


@mock.patch('flash_services.codeship.logger.warning')
def test_unfinished_formatting(warning):
    response = dict(
        repository_name='foo',
        builds=[dict(
            finished_at=None,
            github_username='textbook',
            message='some much longer message',
            started_at='2016-04-01T23:04:03.050Z',
            status='garbage',
        )],
    )

    result = Codeship.format_data(response)

    assert result == dict(
        name='foo',
        builds=[dict(
            author='textbook',
            duration=None,
            elapsed='elapsed time not available',
            message='some much longer...',
            outcome=None,
            started_at=1459551843,
        )],
        health='neutral',
    )
    warning.assert_called_once_with('unknown status: %s', 'garbage')
