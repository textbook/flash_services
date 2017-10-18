from datetime import datetime
from unittest import mock

import pytest
from datetime import timedelta

import responses

from flash_services.coveralls import Coveralls


@pytest.fixture
def service():
    return Coveralls(vcs_name='foo', account='bar', repo='baz')


def test_repo_name(service):
    assert service.repo_name == 'foo/bar/baz'


@pytest.mark.parametrize('build, outcome', [
    (dict(covered_percent=100), 'ok'),
    (dict(covered_percent=85), 'ok'),
    (dict(covered_percent=80), 'ok'),
    (dict(covered_percent=75), 'neutral'),
    (dict(covered_percent=55), 'neutral'),
    (dict(covered_percent=50), 'neutral'),
    (dict(covered_percent=45), 'error'),
    (dict(covered_percent=None), 'error'),
    (dict(), 'error'),
])
@responses.activate
def test_health(build, outcome, service):
    responses.add(
        responses.GET,
        'https://coveralls.io/foo/bar/baz.json?page=1',
        json=dict(builds=[build])
    )

    result = service.update()

    assert result['health'] == outcome


TWO_DAYS_AGO = (datetime.now() - timedelta(days=2, hours=12)).strftime(
    '%Y-%m-%dT%H:%M:%SZ',
)


@responses.activate
def test_update(service):
    responses.add(
        responses.GET,
        'https://coveralls.io/foo/bar/baz.json?page=1',
        json=dict(
            builds=[dict(
                commit_message='[#123456] some message',
                committer_name='Dummy User',
                covered_percent=80,
                created_at=TWO_DAYS_AGO,
            )],
        )
    )

    result = service.update()

    assert result == dict(
        builds=[dict(
            author='Dummy User',
            committed='two days ago',
            coverage='80.0%',
            message_text='some message',
            raw_coverage=80,
        )],
        health='ok',
        name='foo/bar/baz',
    )


@responses.activate
def test_format_build_missing_data(service):
    responses.add(
        responses.GET,
        'https://coveralls.io/foo/bar/baz.json?page=1',
        json=dict(builds=[{}]),
    )

    result = service.update()

    assert result['builds'][0] == dict(
        author='<no author>',
        committed='time not available',
        coverage=None,
        message_text=None,
        raw_coverage=None,
    )


@mock.patch('flash_services.coveralls.logger.error')
@responses.activate
def test_update_failure(error, service):
    responses.add(
        responses.GET,
        'https://coveralls.io/foo/bar/baz.json?page=1',
        status=401,
    )

    result = service.update()

    error.assert_called_once_with('failed to update Coveralls project data')
    assert result == {}
