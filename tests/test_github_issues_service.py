import logging

import pytest
import responses

from flash_services.core import Service
from flash_services.github import GitHubEnterpriseIssues, GitHubIssues


@pytest.fixture
def service():
    return GitHubIssues(api_token='foobar', account='foo', repo='bar')


def test_tracker_service_type():
    assert issubclass(GitHubIssues, Service)


def test_correct_config():
    assert GitHubIssues.AUTH_PARAM == 'access_token'
    assert GitHubIssues.FRIENDLY_NAME == 'GitHub Issues'
    assert GitHubIssues.REQUIRED == {'api_token', 'account', 'repo'}
    assert GitHubIssues.ROOT == 'https://api.github.com'
    assert GitHubIssues.TEMPLATE == 'gh-issues-section'


def test_correct_enterprise_config():
    assert GitHubEnterpriseIssues.AUTH_PARAM == 'access_token'
    assert GitHubEnterpriseIssues.FRIENDLY_NAME == 'GitHub Issues'
    assert GitHubEnterpriseIssues.REQUIRED == {'api_token', 'account', 'repo', 'root'}
    assert GitHubEnterpriseIssues.ROOT == ''
    assert GitHubEnterpriseIssues.TEMPLATE == 'gh-issues-section'


@responses.activate
def test_update_success(service, caplog):
    caplog.set_level(logging.DEBUG)
    responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/issues?state=all&access_token=foobar',
        headers={'User-Agent': 'bar'},
        json=[],
    )

    result = service.update()

    assert 'fetching GitHub Issues project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'issues': {}, 'name': 'foo/bar', 'health': 'neutral', 'halflife': None}


@responses.activate
def test_update_enterprise_success(caplog):
    caplog.set_level(logging.DEBUG)
    responses.add(
        responses.GET,
        'http://dummy.url/repos/foo/bar/issues?state=all&access_token=foobar',
        headers={'User-Agent': 'bar'},
        json=[],
    )
    service = GitHubEnterpriseIssues(
        api_token='foobar',
        account='foo',
        repo='bar',
        root='http://dummy.url',
    )

    result = service.update()

    assert 'fetching GitHub Issues project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    assert result == {'issues': {}, 'name': 'foo/bar', 'health': 'neutral', 'halflife': None}


@responses.activate
def test_update_failure(service, caplog):
    responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/issues?state=all&access_token=foobar',
        headers={'User-Agent': 'bar'},
        status=401,

    )

    result = service.update()

    assert 'failed to update GitHub Issues project data' in [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert result == {}


@pytest.mark.parametrize('payload, expected', [
    ([], dict(name='foo/bar', issues={}, health='neutral', halflife=None)),
    (
        [{'state': 'open'}, {'state': 'open'}],
        dict(name='foo/bar', issues={'open-issues': 2}, health='neutral',
             halflife=None),
    ),
    (
        [{'state': 'open'}, {'state': 'closed'}],
        dict(name='foo/bar', issues={'open-issues': 1, 'closed-issues': 1},
             health='neutral', halflife=None),
    ),
    (
        [{'state': 'open'}, {'state': 'open', 'pull_request': {}}],
        dict(name='foo/bar', issues={'open-issues': 1, 'open-pull-requests':
            1},
             health='neutral', halflife=None),
    ),
    (
        [{'state': 'closed', 'created_at': '2010/11/12', 'closed_at': '2010/11/14'}],
        dict(name='foo/bar', issues={'closed-issues': 1}, health='ok',
             halflife='two days'),
    ),
    (
        [{'state': 'closed', 'created_at': '2010/11/12', 'closed_at': '2010/11/22'}],
        dict(name='foo/bar', issues={'closed-issues': 1}, health='neutral',
             halflife='ten days'),
    ),
    (
        [{'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/11/14'}],
        dict(name='foo/bar', issues={'closed-issues': 1}, health='error',
             halflife='a month'),
    ),
    (
        [
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/15'},
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/16'},
            {'state': 'open', 'created_at': '2010/10/12', 'closed_at': None},
        ],
        dict(name='foo/bar', issues={'closed-issues': 2, 'open-issues': 1},
             health='ok', halflife='three days'),
    ),
    (
        [
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/15'},
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/16', 'pull_request': {}},
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/17'},
            {'state': 'open', 'created_at': '2010/10/12', 'closed_at': None},
        ],
        dict(
            name='foo/bar',
            issues={'closed-issues': 2, 'closed-pull-requests': 1, 'open-issues': 1},
            health='ok',
            halflife='four days',
        ),
    ),
])
@responses.activate
def test_format_data(payload, expected, service):
    responses.add(
        responses.GET,
        'https://api.github.com/repos/foo/bar/issues?state=all&access_token=foobar',
        json=payload,
    )

    assert service.update() == expected
    assert responses.calls[0].request.headers['User-Agent'] == 'bar'


def test_adjust_threshold():
    service = GitHubIssues(ok_threshold=1, account='', repo='', api_token='')
    assert service.ok_threshold == 1
    assert service.neutral_threshold == 30
    issues = [
        {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/15'},
    ]
    assert service.format_data(issues).get('health') == 'neutral'
    service.neutral_threshold = 2
    assert service.format_data(issues).get('health') == 'error'
