from datetime import datetime
from unittest import mock

import pytest
from datetime import timedelta

from flash_services.coveralls import Coveralls


@pytest.fixture()
def service():
    return Coveralls(vcs_name='foo', account='bar', repo='baz')


def test_repo_name(service):
    assert service.repo_name == 'foo/bar/baz'


@mock.patch.object(Coveralls, 'health')
@mock.patch.object(Coveralls, 'format_build')
def test_format_data(format_build, health, service):
    result = service.format_data('foo', dict(builds=['bar']))

    format_build.assert_called_once_with('bar')
    health.assert_called_once_with(format_build.return_value)
    assert result == dict(
        name='foo',
        builds=[format_build.return_value],
        health=health.return_value,
    )


@pytest.mark.parametrize('build, outcome', [
    (dict(raw_coverage=100), 'ok'),
    (dict(raw_coverage=85), 'ok'),
    (dict(raw_coverage=80), 'ok'),
    (dict(raw_coverage=75), 'neutral'),
    (dict(raw_coverage=55), 'neutral'),
    (dict(raw_coverage=50), 'neutral'),
    (dict(raw_coverage=45), 'error'),
    (dict(raw_coverage=None), 'error'),
    (None, 'error'),
])
def test_health(build, outcome, service):
    assert service.health(build) == outcome


TWO_DAYS_AGO = (datetime.now() - timedelta(days=2, hours=12)).strftime(
    '%Y-%m-%dT%H:%M:%SZ',
)


def test_format_build(service):
    result = service.format_build(dict(
        commit_message='some dummy text',
        committer_name='Test Author',
        covered_percent=90,
        created_at=TWO_DAYS_AGO,
    ))

    assert result == dict(
        author='Test Author',
        committed='two days ago',
        coverage='90.0%',
        message_text='some dummy text',
        raw_coverage=90,
    )


@mock.patch('flash_services.coveralls.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': dict(
        builds=[dict(
            commit_message='[#123456] some message',
            committer_name='Dummy User',
            covered_percent=80,
            created_at=TWO_DAYS_AGO,
        )],
    ),
})
def test_update(get, service):
    result = service.update()

    get.expect_called_once_with('https://coveralls.io/foo/bar/baz.json?page=1')
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


def test_format_build_missing_data(service):
    result = service.format_build({})

    assert result == dict(
        author='&lt;no author&gt;',
        committed='time not available',
        coverage=None,
        message_text=None,
        raw_coverage=None,
    )
