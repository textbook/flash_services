import logging

import pytest
import responses

from flash_services.core import Service
from flash_services.travis import TravisPro


@pytest.fixture
def service():
    return TravisPro(account='foo', app='bar', api_token='some_token')


HEADERS = {
    'Accept': 'application/vnd.travis-ci.2+json',
    'User-Agent': 'Flash',
    'Authorization': 'token "some_token"',
}


def test_tracker_service_type():
    assert issubclass(TravisPro, Service)


def test_correct_config():
    assert TravisPro.REQUIRED == {'api_token', 'app', 'account'}
    assert TravisPro.ROOT == 'https://api.travis-ci.com'
    assert TravisPro.TEMPLATE == 'ci-section'


def test_correct_headers(service):
    assert service.headers == HEADERS


def test_update_success(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://api.travis-ci.com/repos/foo/bar/builds',
        json={},
    )

    result = service.update()

    assert 'fetching Travis CI project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'builds': [], 'name': 'foo/bar', 'health': 'neutral'}
    for key in HEADERS:
        assert mocked_responses.calls[0].request.headers[key] == HEADERS[key]


def test_update_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.travis-ci.com/repos/foo/bar/builds',
        status=401,
    )

    result = service.update()

    assert 'failed to update Travis CI project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


def test_formatting(service, mocked_responses):
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
    mocked_responses.add(
        responses.GET,
        'https://api.travis-ci.com/repos/foo/bar/builds',
        json=response,
    )

    result = service.update()

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


def test_unfinished_formatting(service, caplog, mocked_responses):
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
    mocked_responses.add(
        responses.GET,
        'https://api.travis-ci.com/repos/foo/bar/builds',
        json=response,
    )

    result = service.update()

    assert result == dict(
        name='foo/bar',
        builds=[dict(
            author='alice',
            duration=None,
            elapsed='elapsed time not available',
            message='some much longer message',
            outcome=None,
            started_at=None,
        )],
        health='neutral',
    )
    assert 'unknown outcome: garbage' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARN
    ]
