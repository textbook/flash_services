import logging

import pytest
import responses

from flash_services.codeship import Codeship
from flash_services.core import Service


@pytest.fixture
def service():
    return Codeship(api_token='foobar', project_id=123)


def test_tracker_service_type():
    assert issubclass(Codeship, Service)


def test_correct_config():
    assert Codeship.AUTH_PARAM == 'api_key'
    assert Codeship.REQUIRED == {'api_token', 'project_id'}
    assert Codeship.ROOT == 'https://codeship.com/api/v1'
    assert Codeship.TEMPLATE == 'ci-section'


@responses.activate
def test_update_success(service, caplog):
    caplog.set_level(logging.DEBUG)
    responses.add(
        responses.GET,
        'https://codeship.com/api/v1/projects/123.json?api_key=foobar',
        json={'repository_name': 'bar'},
    )

    result = service.update()

    assert 'fetching Codeship project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'builds': [], 'name': 'bar', 'health': 'neutral'}


@responses.activate
def test_update_failure(service, caplog):
    responses.add(
        responses.GET,
        'https://codeship.com/api/v1/projects/123.json?api_key=foobar',
        status=401,
    )

    result = service.update()

    assert 'failed to update Codeship project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


@responses.activate
def test_formatting(service):
    responses.add(
        responses.GET,
        'https://codeship.com/api/v1/projects/123.json?api_key=foobar',
        json=(dict(
            repository_name='foo',
            builds=[dict(
                finished_at='2016-04-01T23:10:06.334Z',
                github_username='textbook',
                message='hello world',
                started_at='2016-04-01T23:04:03.050Z',
                status='success',
            )],
        )),
    )

    result = service.update()

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


@responses.activate
def test_unfinished_formatting(service, caplog):
    responses.add(
        responses.GET,
        'https://codeship.com/api/v1/projects/123.json?api_key=foobar',
        json=(dict(
            repository_name='foo',
            builds=[dict(
                finished_at=None,
                github_username='textbook',
                message='some much longer message',
                started_at='2016-04-01T23:04:03.050Z',
                status='garbage',
            )],
        )),
    )

    result = service.update()

    assert result == dict(
        name='foo',
        builds=[dict(
            author='textbook',
            duration=None,
            elapsed='elapsed time not available',
            message='some much longer message',
            outcome=None,
            started_at=1459551843,
        )],
        health='neutral',
    )
    assert 'unknown outcome: garbage' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARN
    ]
