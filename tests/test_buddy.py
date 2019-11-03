import json
import logging

import pytest
import responses

from flash_services.buddy import Buddy
from flash_services.core import Service


@pytest.fixture
def service():
    return Buddy(api_token='foo', domain='bar', project_name='baz', pipeline_id=123)


@pytest.fixture
def buddy_json():
    """Example from https://buddy.works/docs/api/pipelines/executions/list."""
    with open('buddy.json') as json_file:
        return json.load(json_file)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as requests_mock:
        yield requests_mock


def test_buddy_service_type():
    assert issubclass(Buddy, Service)


def test_correct_config():
    assert Buddy.AUTH_HEADER == 'Authorization'
    assert Buddy.REQUIRED == {'api_token', 'domain', 'project_name', 'pipeline_id'}
    assert Buddy.ROOT == 'https://api.buddy.works'
    assert Buddy.TEMPLATE == 'ci-section'


def test_update_success(service, caplog, mocked_responses, buddy_json):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://api.buddy.works/workspaces/bar/projects/baz/pipelines/123/executions',
        json=buddy_json,
    )

    result = service.update()

    assert mocked_responses.calls[0].request.headers['Authorization'] == 'Bearer foo'
    assert 'fetching Buddy project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {
        'builds': [
            dict(
                author='Mike Benson',
                duration=3,
                elapsed='took two seconds',
                message='init repo\n',
                outcome='passed',
                started_at=1459235480,
            ),
        ],
        'name': 'bar/baz (123)',
        'health': 'ok'
    }


def test_update_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.buddy.works/workspaces/bar/projects/baz/pipelines/123/executions',
        status=401,
    )

    result = service.update()

    assert 'failed to update Buddy project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


@pytest.mark.parametrize('input_, expected,', [
    (dict(author=dict(name='Jane Doe')), 'Jane Doe'),
    (dict(author=dict(title=None), committer=dict(name='Jane Doe')), 'Jane Doe'),
])
def test_get_name(input_, expected):
    assert Buddy.get_name(input_) == expected
