from unittest import mock

import pytest

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


@mock.patch('flash_services.github.logger.debug')
@mock.patch('flash_services.github.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': [],
})
def test_update_success(get, debug, service):
    result = service.update()

    get.assert_called_once_with(
        'https://api.github.com/repos/foo/bar/issues?state=all&access_token=foobar',
        headers={'User-Agent': 'bar'}
    )
    debug.assert_called_once_with('fetching GitHub issue data')
    assert result == {'issues': {}, 'name': 'foo/bar', 'health': 'neutral', 'halflife': None}


@mock.patch('flash_services.github.logger.debug')
@mock.patch('flash_services.github.requests.get', **{
    'return_value.status_code': 200,
    'return_value.json.return_value': [],
})
def test_update_enterprise_success(get, debug):
    service = GitHubEnterpriseIssues(api_token='foobar', account='foo',
                                     repo='bar', root='http://dummy.url')

    result = service.update()

    get.assert_called_once_with(
        'http://dummy.url/repos/foo/bar/issues?state=all&access_token=foobar',
        headers={'User-Agent': 'bar'}
    )
    debug.assert_called_once_with('fetching GitHub issue data')
    assert result == {'issues': {}, 'name': 'foo/bar', 'health': 'neutral', 'halflife': None}


@mock.patch('flash_services.github.logger.error')
@mock.patch('flash_services.github.requests.get', **{
    'return_value.status_code': 401,
})
def test_update_failure(get, error, service):
    result = service.update()

    get.assert_called_once_with(
        'https://api.github.com/repos/foo/bar/issues?state=all&access_token=foobar',
        headers={'User-Agent': 'bar'}
    )
    error.assert_called_once_with('failed to update GitHub issue data')
    assert result == {}


@pytest.mark.parametrize('input_, expected', [
    (('hello', []), dict(name='hello', issues={}, health='neutral', halflife=None)),
    (
        ('hello', [{'state': 'open'}, {'state': 'open'}]),
        dict(name='hello', issues={'open-issues': 2}, health='neutral', halflife=None),
    ),
    (
        ('hello', [{'state': 'open'}, {'state': 'closed'}]),
        dict(name='hello', issues={'open-issues': 1, 'closed-issues': 1}, health='neutral', halflife=None),
    ),
    (
        ('hello', [{'state': 'open'}, {'state': 'open', 'pull_request': {}}]),
        dict(name='hello', issues={'open-issues': 1, 'open-pull-requests': 1}, health='neutral', halflife=None),
    ),
    (
        ('hello', [{'state': 'closed', 'created_at': '2010/11/12', 'closed_at': '2010/11/14'}]),
        dict(name='hello', issues={'closed-issues': 1}, health='ok', halflife='two days'),
    ),
    (
        ('hello', [{'state': 'closed', 'created_at': '2010/11/12', 'closed_at': '2010/11/22'}]),
        dict(name='hello', issues={'closed-issues': 1}, health='neutral', halflife='ten days'),
    ),
    (
        ('hello', [{'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/11/14'}]),
        dict(name='hello', issues={'closed-issues': 1}, health='error', halflife='a month'),
    ),
    (
        ('hello', [
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/15'},
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/16'},
            {'state': 'open', 'created_at': '2010/10/12', 'closed_at': None},
        ]),
        dict(name='hello', issues={'closed-issues': 2, 'open-issues': 1}, health='ok', halflife='three days'),
    ),
    (
        ('hello', [
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/15'},
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/16', 'pull_request': {}},
            {'state': 'closed', 'created_at': '2010/10/12', 'closed_at': '2010/10/17'},
            {'state': 'open', 'created_at': '2010/10/12', 'closed_at': None},
        ]),
        dict(
            name='hello',
            issues={'closed-issues': 2, 'closed-pull-requests': 1, 'open-issues': 1},
            health='ok',
            halflife='four days',
        ),
    ),
])
def test_format_data(input_, expected):
    assert GitHubIssues.format_data(*input_) == expected
