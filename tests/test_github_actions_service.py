import logging

import pytest
import responses

from flash_services.core import ContinuousIntegrationService
from flash_services.github import GitHubActions, GitHubEnterpriseActions
from flash_services.utils import Outcome


@pytest.fixture
def service():
    return GitHubActions(username='user', password='foobar', account='foo', repo='bar')


def test_service_type():
    assert issubclass(GitHubActions, ContinuousIntegrationService)
    assert GitHubActions.TEMPLATE == 'ci-section'


def test_update_success(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/actions/runs?per_page=100',
        json=dict(total_count=0, workflow_runs=[]),
    )

    result = service.update()

    assert 'fetching GitHub Actions project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'builds': [], 'name': 'foo/bar', 'health': 'neutral'}
    headers = mocked_responses.calls[0].request.headers
    assert headers['Accept'] == 'application/vnd.github.v3+json'
    assert headers['Authorization'] == 'Basic dXNlcjpmb29iYXI='
    assert headers['User-Agent'] == 'bar'


def test_update_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/actions/runs?per_page=100',
        status=401,
    )

    result = service.update()

    assert 'failed to update GitHub Actions project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


def test_passing_build(service, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/actions/runs?per_page=100',
        json={
            "workflow_runs": [
                {
                    "conclusion": "success",
                    "created_at": "2016-04-14T20:47:40Z",
                    "head_commit": {
                        "message": "I did some work",
                        "author": {
                            "name": "Jane Doe"
                        }
                    },
                    "status": "completed",
                    "updated_at": "2016-04-14T20:57:07Z"
                }
            ]
        }
    )

    result = service.update()

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
        name='foo/bar',
        health='ok'
    )


def test_failing_build(service, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/actions/runs?per_page=100',
        json={
            "workflow_runs": [
                {
                    "conclusion": "failure",
                    "created_at": "2016-04-14T20:47:40Z",
                    "head_commit": {
                        "message": "I did some bad work",
                        "author": {
                            "name": "Jane Doe"
                        }
                    },
                    "status": "completed",
                    "updated_at": "2016-04-14T20:57:07Z"
                }
            ]
        }
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
        name='foo/bar',
        health='error'
    )


# See https://docs.github.com/en/rest/reference/checks#create-a-check-run
@pytest.mark.parametrize('status, conclusion, outcome', [
    ('in_progress', None, Outcome.WORKING),
    ('queued', None, Outcome.WORKING),
    ('completed', 'success', Outcome.PASSED),
    ('completed', 'failure', Outcome.FAILED),
    ('completed', 'action_required', Outcome.CRASHED),
    ('completed', 'cancelled', Outcome.CANCELLED),
    ('completed', 'neutral', Outcome.PASSED),
    ('completed', 'skipped', Outcome.CANCELLED),
    ('completed', 'stale', Outcome.CRASHED),
    ('completed', 'timed_out', Outcome.CRASHED),
])
def test_combines_status_and_conclusion(status, conclusion, outcome, service):
    formatted = service.format_build(dict(status=status, conclusion=conclusion))
    assert formatted['outcome'] == outcome


def test_working_build(service, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/actions/runs?per_page=100',
        json={
            "workflow_runs": [
                {
                    "created_at": "2016-04-14T20:47:40Z",
                    "head_commit": {
                        "message": "I did some more work",
                        "author": {
                            "name": "Jane Doe"
                        }
                    },
                    "status": "in_progress",
                    "updated_at": "2016-04-14T20:47:40Z"
                }, {
                    "conclusion": "success",
                    "created_at": "2016-04-14T20:47:40Z",
                    "head_commit": {
                        "message": "I did some work",
                        "author": {
                            "name": "Jane Doe"
                        }
                    },
                    "status": "completed",
                    "updated_at": "2016-04-14T20:57:07Z"
                }
            ]
        },
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


def test_actions_enterprise_update(caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'http://dummy.url/repos/foo/bar/actions/runs?per_page=100',
        json=dict(total_count=0, workflow_runs=[]),
    )
    service = GitHubEnterpriseActions(
        username='enterprise-user',
        password='foobar',
        account='foo',
        repo='bar',
        root='http://dummy.url',
    )

    result = service.update()

    assert 'fetching GitHub Actions project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == dict(builds=[], name='foo/bar', health='neutral')
    headers = mocked_responses.calls[0].request.headers
    assert headers['Accept'] == 'application/vnd.github.v3+json'
    assert headers['Authorization'] == 'Basic ZW50ZXJwcmlzZS11c2VyOmZvb2Jhcg=='
    assert headers['User-Agent'] == 'bar'
