import logging
from datetime import datetime, timedelta

import pytest
import responses

from flash_services.core import Service
from flash_services.github import GitHub, GitHubEnterprise


@pytest.fixture
def service():
    return GitHub(api_token='foobar', account='foo', repo='bar')


@pytest.fixture
def branched():
    return GitHub(api_token='foobar', account='foo', repo='bar', branch='baz')


def test_tracker_service_type():
    assert issubclass(GitHub, Service)


def test_correct_config():
    assert GitHub.AUTH_PARAM == 'access_token'
    assert GitHub.FRIENDLY_NAME == 'GitHub'
    assert GitHub.REQUIRED == {'api_token', 'account', 'repo'}
    assert GitHub.ROOT == 'https://api.github.com'
    assert GitHub.TEMPLATE == 'vcs-section'


def test_correct_enterprise_config():
    assert GitHubEnterprise.AUTH_PARAM == 'access_token'
    assert GitHubEnterprise.FRIENDLY_NAME == 'GitHub'
    assert GitHubEnterprise.REQUIRED == {'api_token', 'account', 'repo', 'root'}
    assert GitHubEnterprise.ROOT == ''
    assert GitHubEnterprise.TEMPLATE == 'vcs-section'


TWO_DAYS_AGO = (datetime.now() - timedelta(days=2, hours=12)).strftime(
    '%Y-%m-%dT%H:%M:%SZ',
)


def test_update_success(service, caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/commits?access_token=foobar',
        json=[{'commit': {
            'author': {'name': 'alice'},
            'committer': {'name': 'bob', 'date': TWO_DAYS_AGO},
            'message': 'commit message',
        }}],
    )

    result = service.update()

    assert 'fetching GitHub project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'commits': [{
        'message': 'commit message',
        'author': 'alice [bob]',
        'committed': 'two days ago'
    }], 'name': 'foo/bar'}
    assert mocked_responses.calls[0].request.headers['User-Agent'] == 'bar'


def test_update_enterprise_success(caplog, mocked_responses):
    caplog.set_level(logging.DEBUG)
    mocked_responses.add(
        responses.GET,
        'http://dummy.url/repos/foo/bar/commits?access_token=foobar',
        json=[{'commit': {
            'author': {'name': 'alice'},
            'committer': {'name': 'bob', 'date': TWO_DAYS_AGO},
            'message': 'commit message',
        }}],
    )

    service = GitHubEnterprise(api_token='foobar', account='foo', repo='bar',
                               root='http://dummy.url')

    result = service.update()

    assert 'fetching GitHub project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'commits': [{
        'message': 'commit message',
        'author': 'alice [bob]',
        'committed': 'two days ago'
    }], 'name': 'foo/bar'}
    assert mocked_responses.calls[0].request.headers['User-Agent'] == 'bar'


def test_update_failure(service, caplog, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/commits?access_token=foobar',
        status=401,
    )

    result = service.update()

    assert 'failed to update GitHub project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}
    assert mocked_responses.calls[0].request.headers['User-Agent'] == 'bar'


@pytest.mark.parametrize('commit, expected', [
    (dict(), dict(author='<no author>', committed='time not available', message='')),
    (
        dict(
            author=dict(name='alice'),
            committer=dict(name='bob'),
            message='hello world',
        ),
        dict(
            author='alice [bob]',
            committed='time not available',
            message='hello world',
        ),
    ),
    (
        dict(author=dict(name='alice'), message='hello world fixes foo/bar#3'),
        dict(
            author='alice',
            committed='time not available',
            message='hello world',
        ),
    ),
    (
        dict(committer=dict(name='bob'), message='hello world'),
        dict(
            author='bob',
            committed='time not available',
            message='hello world',
        ),
    ),
])
def test_format_commit(service, commit, expected, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/commits?access_token=foobar',
        json=[dict(commit=commit)],
    )

    result = service.update()

    assert result['commits'][0] == expected
    assert mocked_responses.calls[0].request.headers['User-Agent'] == 'bar'


def test_branch_url(branched, mocked_responses):
    mocked_responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/commits?sha=baz&access_token=foobar',
        status=302,
    )

    branched.update()

    assert mocked_responses.calls[0].request.headers['User-Agent'] == 'bar'
