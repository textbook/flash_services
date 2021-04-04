import logging
import pytest
import responses

from flash_services.circleci import CircleCI
from flash_services.core import ContinuousIntegrationService


@pytest.fixture
def service():
    return CircleCI(
        api_token='banana',
        vcs_type='foo',
        username='bar',
        project='baz',
        branch='qux'
    )


def test_service_type():
    assert issubclass(CircleCI, ContinuousIntegrationService)


def test_update_success(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        json=[]
    )

    result = service.update()

    assert 'fetching CircleCI project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'builds': [], 'name': 'foo/bar/baz [qux]', 'health': 'neutral'}
    assert mocked_responses.calls[0].request.headers['Accept'] == 'application/json'
    assert mocked_responses.calls[0].request.headers['Circle-Token'] == 'banana'


def test_passing_build(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        json=[
            {
                "committer_name": "Jane Doe",
                "subject": "I did some work",
                "start_time": "2016-04-14T20:47:40Z",
                "status": "success",
                "stop_time": "2016-04-14T20:57:07Z"
            }
        ]
    )

    result = service.update()

    assert 'fetching CircleCI project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == dict(
        builds=[
            dict(
                author='Jane Doe',
                duration=567,
                elapsed='took nine minutes',
                message='I did some work',
                outcome='passed',
                started_at=1460666860,
            )
        ],
        name='foo/bar/baz [qux]',
        health='ok'
    )


def test_update_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        status=401,
    )

    result = service.update()

    assert 'failed to update CircleCI project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


def test_working_build(service, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        json=[
            {
                "committer_name": "Jane Doe",
                "subject": "I did some more work",
                "start_time": "2016-04-14T20:47:40Z",
                "status": "running"
            }, {
                "committer_name": "Jane Doe",
                "subject": "I did some work",
                "start_time": "2016-04-14T20:47:40Z",
                "status": "success",
                "stop_time": "2016-04-14T20:57:07Z"
            }
        ]
    )

    result = service.update()

    assert result['builds'][0] == dict(
        author='Jane Doe',
        duration=None,
        elapsed='nearly done',
        message='I did some more work',
        outcome='working',
        started_at=1460666860,
    )


def test_failing_build(service, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        json=[
            {
                "committer_name": "Jane Doe",
                "subject": "I did some bad work",
                "start_time": "2016-04-14T20:47:40Z",
                "status": "failed",
                "stop_time": "2016-04-14T20:57:07Z"
            }
        ]
    )

    result = service.update()

    assert result == dict(
        builds=[
            dict(
                author='Jane Doe',
                duration=567,
                elapsed='took nine minutes',
                message='I did some bad work',
                outcome='failed',
                started_at=1460666860,
            )
        ],
        name='foo/bar/baz [qux]',
        health='error'
    )


def test_uses_author_name_if_available(service, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://circleci.com/api/v1.1/project/foo/bar/baz/tree/qux?limit=100&shallow=true',
        json=[
            {
                "author_name": "Jane Doe",
                "committer_name": "GitHub",
                "subject": "I did some bad work",
                "start_time": "2016-04-14T20:47:40Z",
                "status": "failed",
                "stop_time": "2016-04-14T20:57:07Z"
            }
        ]
    )

    result = service.update()

    assert result['builds'][0]['author'] == 'Jane Doe'
