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
    assert result == {'issues': {}, 'name': 'foo/bar'}


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
    assert result == {'issues': {}, 'name': 'foo/bar'}


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
    (('hello', []), dict(name='hello', issues={})),
    (
        ('hello', [{'state': 'open'}, {'state': 'open'}]),
        dict(name='hello', issues={'open-issues': 2}),
    ),
    (
        ('hello', [{'state': 'open'}, {'state': 'closed'}]),
        dict(name='hello', issues={'open-issues': 1, 'closed-issues': 1}),
    ),
    (
        ('hello', [{'state': 'open'}, {'state': 'open', 'pull_request': {}}]),
        dict(name='hello', issues={'open-issues': 1, 'open-pull-requests': 1}),
    ),
])
def test_format_data(input_, expected):
    assert GitHubIssues.format_data(*input_) == expected
